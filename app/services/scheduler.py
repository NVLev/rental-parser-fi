import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.database.db_helper import db_helper
from app.database.models import UserFilter
from app.parsers.sato import SatoParser
from app.parsers.vuokraovi import VuokraoviParser
from app.services.listing_service import ListingService
from bot.routers.listings import _format_listing
from bot.user_filter_service import UserFilterService
from config import settings

logger = logging.getLogger(__name__)


async def run_parse_and_notify(bot: Bot) -> None:
    """Парсинг + уведомления. Запускается по расписанию."""
    logger.info("Scheduler: starting parse job")

    all_listings = []
    try:
        async with VuokraoviParser() as parser:
            all_listings.extend(await parser.parse())
        logger.info("Scheduler: Vuokraovi done, %d listings", len(all_listings))
    except Exception as e:
        logger.error("Scheduler: VuokraoviParser failed: %s", e)

    try:
        async with SatoParser() as parser:
            sato = await parser.parse()
            all_listings.extend(sato)
        logger.info("Scheduler: SATO done, %d listings", len(sato))
    except Exception as e:
        logger.error("Scheduler: SatoParser failed: %s", e)

    if not all_listings:
        logger.warning(
            "Scheduler: no listings parsed, skipping upsert and notifications"
        )
        return

    async with db_helper.session_factory() as session:
        service = ListingService(session)
        new_count = await service.upsert_listings(all_listings)

        vuokraovi_ids = [l.external_id for l in all_listings if l.source == "vuokraovi"]
        sato_ids = [l.external_id for l in all_listings if l.source == "sato"]
        deactivated = 0
        deactivated += await service.deactivate_missing(
            vuokraovi_ids, source="vuokraovi"
        )
        deactivated += await service.deactivate_missing(sato_ids, source="sato")

    logger.info(
        "Scheduler: upsert done — new=%d, deactivated=%d", new_count, deactivated
    )

    if new_count == 0:
        logger.info("Scheduler: no new listings, skipping notifications")
        return

    await _send_notifications(bot)


async def _send_notifications(bot: Bot) -> None:
    """Рассылает уведомления всем пользователям с активными подписками."""
    from sqlalchemy import select

    from app.database.models import UserFilter

    async with db_helper.session_factory() as session:
        result = await session.execute(
            select(UserFilter).where(UserFilter.is_active == True)
        )
        filters = result.scalars().all()

    logger.info("Scheduler: sending notifications to %d subscribers", len(filters))

    for user_filter in filters:
        try:
            await _notify_user(bot, user_filter)
        except Exception as e:
            logger.error(
                "Scheduler: failed to notify user %s: %s", user_filter.user_id, e
            )


async def _notify_user(bot: Bot, user_filter: UserFilter) -> None:
    async with db_helper.session_factory() as session:
        service = UserFilterService(session)
        new_listings = await service.get_new_listings_for_user(user_filter, limit=10)

        if not new_listings:
            return

        listing_ids = [l.id for l in new_listings]
        await service.mark_as_seen(user_filter.user_id, listing_ids)

    logger.info(
        "Scheduler: notifying user %s — %d new listings",
        user_filter.user_id,
        len(new_listings),
    )

    await bot.send_message(
        user_filter.user_id,
        f"🔔 <b>{len(new_listings)} new listing(s) match your filters!</b>",
    )
    for listing in new_listings:
        try:
            await bot.send_message(
                user_filter.user_id,
                _format_listing(listing),
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.warning(
                "Failed to send listing %s to user %s: %s",
                listing.external_id,
                user_filter.user_id,
                e,
            )


def create_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_parse_and_notify,
        trigger=IntervalTrigger(minutes=settings.parser.check_interval_minutes),
        args=[bot],
        id="parse_and_notify",
        replace_existing=True,
        misfire_grace_time=60,  # если задача опоздала на 60 сек — всё равно запустить
    )
    return scheduler
