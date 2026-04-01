from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Listing


class ListingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_listings(self, listings: List[Listing]) -> int:
        """
        Сохраняет объявления в БД.

        - добавляет новые
        - обновляет существующие
        - возвращает количество новых объявлений
        """

        new_count = 0

        for listing in listings:
            stmt = select(Listing).where(
                Listing.external_id == listing.external_id
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # обновляем поля
                existing.price = listing.price
                existing.area = listing.area
                existing.district = listing.district
                existing.address = listing.address
                existing.published_at = listing.published_at
                existing.is_active = True
            else:
                self.session.add(listing)
                new_count += 1

        await self.session.commit()
        return new_count