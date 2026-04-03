from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Listing


class ListingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_listings(self, listings: List[Listing]) -> int:
        """Сохраняет объявления в БД, обновляет существующие. Возвращает кол-во новых."""
        if not listings:
            return 0

        # Получаем все существующие external_id
        existing_ids = {
            row
            for row in (
                await self.session.execute(
                    select(Listing.external_id).where(
                        Listing.external_id.in_([l.external_id for l in listings])
                    )
                )
            ).scalars()
        }

        new_count = 0

        for listing in listings:
            if listing.external_id in existing_ids:
                stmt = select(Listing).where(
                    Listing.external_id == listing.external_id
                )
                result = await self.session.execute(stmt)
                existing = result.scalar_one()
                existing.price = listing.price
                existing.area = listing.area
                existing.available_from = listing.available_from
                existing.is_active = True
            else:
                self.session.add(listing)
                new_count += 1

        await self.session.commit()
        return new_count

    async def get_listings(
            self,
            price_min: Optional[float] = None,
            price_max: Optional[float] = None,
            area_min: Optional[float] = None,
            area_max: Optional[float] = None,
            district: Optional[str] = None,
            room_count: Optional[str] = None,
            water_included: Optional[bool] = None,
            source: Optional[str] = None,
            limit: int = 20,
            offset: int = 0,
    ) -> List[Listing]:
        """Возвращает объявления с фильтрами."""
        stmt = select(Listing).where(Listing.is_active == True)

        if price_min is not None:
            stmt = stmt.where(Listing.price >= price_min)
        if price_max is not None:
            stmt = stmt.where(Listing.price <= price_max)
        if area_min is not None:
            stmt = stmt.where(Listing.area >= area_min)
        if area_max is not None:
            stmt = stmt.where(Listing.area <= area_max)
        if district:
            stmt = stmt.where(Listing.district.ilike(f"%{district}%"))
        if room_count:
            stmt = stmt.where(Listing.room_count == room_count)
        if water_included is not None:
            stmt = stmt.where(Listing.water_included == water_included)
        if source:
            stmt = stmt.where(Listing.source == source)

        stmt = stmt.order_by(Listing.published_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())