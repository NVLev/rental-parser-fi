from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.parsers.vuokraovi import VuokraoviParser
from app.services.listing_service import ListingService
from app.database.db_helper import db_helper

router = APIRouter(prefix="/listings", tags=["listings"])


@router.post("/parse")
async def parse_listings(
        session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Запускает парсинг Vuokraovi и сохраняет данные в БД.
    """
    async with VuokraoviParser() as parser:
        listings = await parser.parse()

    service = ListingService(session)
    new_count = await service.upsert_listings(listings)

    return {
        "parsed": len(listings),
        "new": new_count,
    }
