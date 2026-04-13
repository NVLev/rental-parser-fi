from typing import List, Optional
import logging
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Listing

logger = logging.getLogger(__name__)

class ListingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_listings(self, listings: List[Listing]) -> int:
        if not listings:
            return 0

        # Bulk fetch существующих
        keys = [(l.source, l.external_id) for l in listings]
        stmt = select(Listing).where(
            tuple_(Listing.source, Listing.external_id).in_(keys)
        )
        result = await self.session.execute(stmt)
        existing_map: dict[tuple, Listing] = {
            (row.source, row.external_id): row
            for row in result.scalars().all()
        }

        new_count = 0
        for listing in listings:
            key = (listing.source, listing.external_id)
            if key in existing_map:
                existing = existing_map[key]
                existing.price = listing.price
                existing.area = listing.area
                existing.available_from = listing.available_from
                existing.district = listing.district
                existing.water_included = listing.water_included
                existing.water_price = listing.water_price
                existing.electricity_included = listing.electricity_included
                existing.floor_plan_url = listing.floor_plan_url
                existing.lessor_name = listing.lessor_name
                existing.is_private_lessor = listing.is_private_lessor
                existing.is_active = True
            else:
                self.session.add(listing)
                existing_map[key] = listing
                new_count += 1

        await self.session.commit()
        return new_count

    async def deactivate_missing(self, parsed_external_ids: List[str], source: str) -> int:
        """
        Помечает is_active=False объявления которых больше нет в выборке парсера.
        Вызывать после upsert_listings.
        """
        stmt = select(Listing).where(
            Listing.source == source,
            Listing.is_active == True,
            Listing.external_id.not_in(parsed_external_ids),
        )
        result = await self.session.execute(stmt)
        stale = result.scalars().all()

        for listing in stale:
            listing.is_active = False

        await self.session.commit()
        return len(stale)

    async def get_listings(
        self,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        area_min: Optional[float] = None,
        area_max: Optional[float] = None,
        district: Optional[str] = None,
        room_count: Optional[str] = None,
        water_included: Optional[bool] = None,
        is_private_lessor: Optional[bool] = None,
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
        if is_private_lessor is not None:
            stmt = stmt.where(Listing.is_private_lessor == is_private_lessor)
        if source:
            stmt = stmt.where(Listing.source == source)

        stmt = stmt.order_by(Listing.published_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())