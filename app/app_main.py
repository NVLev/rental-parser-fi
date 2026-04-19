from contextlib import asynccontextmanager

import logging
import uvicorn
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import FastAPI

from app.database.db_helper import db_helper
from app.routers import listings
from app.services.scheduler import create_scheduler
from config import settings

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("🚀 Приложение запущено. Подключение к БД готово.")

    bot = Bot(
        token=settings.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    scheduler = create_scheduler(bot)
    scheduler.start()
    logger.info(
        "⏰ Scheduler started, interval=%d min",
        settings.parser.check_interval_minutes,
    )
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        await db_helper.dispose()
        logger.info("🔌 Соединение с БД закрыто.")


app = FastAPI(lifespan=lifespan, title="Rental Parser FI")

app.include_router(listings.router)


if __name__ == "__main__":
    uvicorn.run("app_main:app", host="0.0.0.0", port=8000)
