import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Listing, SeenListing, UserFilter

logger = logging.getLogger(__name__)


class UserFilterService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_filter(self, user_id: int) -> Optional[UserFilter]:
        stmt = select(UserFilter).where(
            UserFilter.user_id == user_id,
            UserFilter.is_active == True,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_filter(self, user_id: int, data: dict) -> UserFilter:
        """Создаёт или обновляет фильтр пользователя."""
        existing = await self.get_filter(user_id)

        # FSM хранит room_count (str) и district (str) — конвертируем в формат модели
        districts = data.get("districts") or (
            data["district"] if data.get("district") else None
        )
        room_counts = data.get("room_counts") or (
            data["room_count"] if data.get("room_count") else None
        )

        if existing:
            existing.source = data.get("source", "both")
            existing.price_min = data.get("price_min")
            existing.price_max = data.get("price_max")
            existing.area_min = data.get("area_min")
            existing.area_max = data.get("area_max")
            existing.districts = districts
            existing.room_counts = room_counts
            existing.water_included_only = bool(data.get("water_included"))
            existing.is_ara = data.get("is_ara")
            existing.electricity_included_only = bool(data.get("electricity_included"))
            existing.is_private_lessor = data.get("is_private_lessor")
            existing.is_student_home = data.get("is_student_home")
            existing.is_active = True
            await self.session.commit()
            logger.info("Updated filter for user %s", user_id)
            return existing
        else:
            user_filter = UserFilter(
                user_id=user_id,
                source=data.get("source", "both"),
                price_min=data.get("price_min"),
                price_max=data.get("price_max"),
                area_min=data.get("area_min"),
                area_max=data.get("area_max"),
                districts=districts,
                room_counts=room_counts,
                water_included_only=bool(data.get("water_included")),
                electricity_included_only=bool(data.get("electricity_included")),
                is_private_lessor=data.get("is_private_lessor"),
                is_ara=data.get("is_ara"),
                is_student_home=data.get("is_student_home"),
            )
            self.session.add(user_filter)
            await self.session.commit()
            logger.info("Created filter for user %s", user_id)
            return user_filter

    async def deactivate_filter(self, user_id: int) -> bool:
        existing = await self.get_filter(user_id)
        if not existing:
            return False
        existing.is_active = False
        await self.session.commit()
        logger.info("Deactivated filter for user %s", user_id)
        return True

    async def get_new_listings_for_user(
        self, user_filter: UserFilter, limit: int = 10
    ) -> list[Listing]:
        """
        Возвращает активные объявления по фильтру пользователя,
        которые он ещё не видел (нет в seen_listings).
        """
        from app.services.listing_service import ListingService

        # Seen listing IDs для этого пользователя
        seen_stmt = select(SeenListing.listing_id).where(
            SeenListing.user_id == user_filter.user_id
        )
        seen_result = await self.session.execute(seen_stmt)
        seen_ids = {row for row in seen_result.scalars()}

        # Применяем фильтры из UserFilter
        stmt = select(Listing).where(Listing.is_active == True)

        if user_filter.price_min is not None:
            stmt = stmt.where(Listing.price >= user_filter.price_min)
        if user_filter.price_max is not None:
            stmt = stmt.where(Listing.price <= user_filter.price_max)
        if user_filter.area_min is not None:
            stmt = stmt.where(Listing.area >= user_filter.area_min)
        if user_filter.area_max is not None:
            stmt = stmt.where(Listing.area <= user_filter.area_max)
        if user_filter.water_included_only:
            stmt = stmt.where(Listing.water_included == True)
        if user_filter.electricity_included_only:  # новое
            stmt = stmt.where(Listing.electricity_included == True)
        if user_filter.is_private_lessor is not None:  # новое
            stmt = stmt.where(Listing.is_private_lessor == user_filter.is_private_lessor)
        if user_filter.is_ara is not None:  # новое
            stmt = stmt.where(Listing.is_ara == user_filter.is_ara)
        if user_filter.is_student_home is not None:  # новое
            stmt = stmt.where(Listing.is_student_home == user_filter.is_student_home)
        if user_filter.source and user_filter.source != "both":
            stmt = stmt.where(Listing.source == user_filter.source)

        # districts — список через запятую
        if user_filter.districts:
            district_list = [d.strip() for d in user_filter.districts.split(",")]
            from sqlalchemy import or_

            stmt = stmt.where(
                or_(*[Listing.district.ilike(f"%{d}%") for d in district_list])
            )

        # room_counts — список через запятую
        if user_filter.room_counts:
            room_list = [r.strip() for r in user_filter.room_counts.split(",")]
            stmt = stmt.where(Listing.room_count.in_(room_list))

        # Исключаем уже виденные
        if seen_ids:
            stmt = stmt.where(Listing.id.not_in(seen_ids))

        stmt = stmt.order_by(Listing.published_at.desc()).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_as_seen(self, user_id: int, listing_ids: list[int]) -> None:
        """Помечает объявления как отправленные пользователю."""
        for listing_id in listing_ids:
            seen = SeenListing(user_id=user_id, listing_id=listing_id)
            self.session.add(seen)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            logger.warning(
                "Some seen_listings already exist for user %s, skipping", user_id
            )

    @staticmethod
    def format_filter_summary(f: UserFilter) -> str:
        lines = ["<b>Your subscription:</b>"]
        if f.price_min or f.price_max:
            lines.append(f"💶 Price: {f.price_min or '—'} – {f.price_max or '—'} €")
        if f.area_min or f.area_max:
            lines.append(f"📐 Area: {f.area_min or '—'} – {f.area_max or '—'} m²")
        if f.room_counts:
            lines.append(f"🚪 Rooms: {f.room_counts}")
        if f.districts:
            lines.append(f"📍 Districts: {f.districts}")
        if f.water_included_only:
            lines.append("💧 Water included only")
        if f.electricity_included_only:
            lines.append("⚡ Electricity included only")
        if f.is_private_lessor is not None:
            lines.append(f"👤 Lessor: {'private' if f.is_private_lessor else 'agency'}")
        if f.is_ara is not None:
            lines.append(f"🏛 ARA: {'only' if f.is_ara else 'excluded'}")
        if f.is_student_home is not None:
            lines.append(f"🎓 Student housing: {'only' if f.is_student_home else 'excluded'}")
        if f.source and f.source != "both":
            lines.append(f"🌐 Source: {f.source}")
        return "\n".join(lines)
