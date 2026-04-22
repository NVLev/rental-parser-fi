import logging
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Listing

logger = logging.getLogger(__name__)


class ListingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_listings(self, listings: List[Listing]) -> int:
        if not listings:
            return 0

        BATCH_SIZE = 1000
        new_count = 0

        for i in range(0, len(listings), BATCH_SIZE):
            batch = listings[i : i + BATCH_SIZE]

            values = [
                {
                    "external_id": l.external_id,
                    "source": l.source,
                    "url": l.url,
                    "price": l.price,
                    "area": l.area,
                    "district": l.district,
                    "address": l.address,
                    "room_count": l.room_count,
                    "room_structure": l.room_structure,
                    "water_included": l.water_included,
                    "water_price": l.water_price,
                    "electricity_included": l.electricity_included,
                    "floor_plan_url": l.floor_plan_url,
                    "available_from": l.available_from,
                    "lessor_name": l.lessor_name,
                    "is_private_lessor": l.is_private_lessor,
                    "published_at": l.published_at,
                    "is_active": True,
                }
                for l in batch
            ]

            stmt = pg_insert(Listing).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["source", "external_id"],
                set_={
                    "price": stmt.excluded.price,
                    "area": stmt.excluded.area,
                    "address": stmt.excluded.address,
                    "available_from": stmt.excluded.available_from,
                    "district": stmt.excluded.district,
                    "water_included": stmt.excluded.water_included,
                    "water_price": stmt.excluded.water_price,
                    "electricity_included": stmt.excluded.electricity_included,
                    "floor_plan_url": stmt.excluded.floor_plan_url,
                    "lessor_name": stmt.excluded.lessor_name,
                    "is_private_lessor": stmt.excluded.is_private_lessor,
                    "is_active": True,
                },
            ).returning(
                Listing.id,
                sa.text("(xmax = 0) AS is_new"),
            )

            result = await self.session.execute(stmt)
            new_count += sum(1 for _, is_new in result if is_new)

        await self.session.commit()
        return new_count

    async def deactivate_missing(
        self, parsed_external_ids: List[str], source: str
    ) -> int:
        """
        Помечает is_active=False объявления которых больше нет в выборке парсера.
        Вызывать после upsert_listings.
        """
        BATCH_SIZE = 1000
        parsed_set = set(parsed_external_ids)
        stmt = select(Listing).where(
            Listing.source == source,
            Listing.is_active == True,
        )

        result = await self.session.stream(stmt)

        stale_count = 0
        batch = []

        async for listing in result.scalars():
            if listing.external_id not in parsed_set:
                listing.is_active = False
                batch.append(listing)

            if len(batch) >= BATCH_SIZE:
                await self.session.flush()
                stale_count += len(batch)
                batch.clear()

        if batch:
            await self.session.flush()
            stale_count += len(batch)

        await self.session.commit()
        return stale_count

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
