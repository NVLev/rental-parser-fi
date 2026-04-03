from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.parsers.vuokraovi import VuokraoviParser
from app.services.listing_service import ListingService
from app.database.schemas.listing import ListingRead
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

@router.get("/", response_model=dict)
async def get_listings(
    session: AsyncSession = Depends(db_helper.session_getter),
    price_min: Optional[float] = Query(None, description="Минимальная цена €/мес"),
    price_max: Optional[float] = Query(None, description="Максимальная цена €/мес"),
    area_min: Optional[float] = Query(None, description="Минимальная площадь м²"),
    area_max: Optional[float] = Query(None, description="Максимальная площадь м²"),
    district: Optional[str] = Query(None, description="Район, например Kallio"),
    room_count: Optional[str] = Query(None, description="ONE_ROOM / TWO_ROOMS / THREE_ROOMS"),
    water_included: Optional[bool] = Query(None, description="Вода включена в аренду"),
    source: Optional[str] = Query(None, description="vuokraovi / sato"),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
):
    """Возвращает список объявлений с фильтрами."""
    service = ListingService(session)
    listings = await service.get_listings(
        price_min=price_min,
        price_max=price_max,
        area_min=area_min,
        area_max=area_max,
        district=district,
        room_count=room_count,
        water_included=water_included,
        source=source,
        limit=limit,
        offset=offset,
    )
    return {"total": len(listings), "listings": [ListingRead.model_validate(l) for l in listings]}