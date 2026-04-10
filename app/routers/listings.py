import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.parsers.sato import SatoParser
from app.parsers.vuokraovi import VuokraoviParser
from app.services.listing_service import ListingService
from app.database.schemas.listing import ListingRead
from app.database.db_helper import db_helper

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/listings", tags=["listings"])


@router.post("/parse")
async def parse_listings(
        session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Запускает парсинг Vuokraovi и сохраняет данные в БД.
    """
    all_listings = []

    async with VuokraoviParser() as parser:
        logger.info("Started VuokraoviParser")
        all_listings.extend(await parser.parse())

    async with SatoParser() as parser:
        sato = await parser.parse()
        logger.info("SATO parsed: %d", len(sato))
        all_listings.extend(sato)

    service = ListingService(session)
    new_count = await service.upsert_listings(all_listings)

    vuokraovi_ids = [l.external_id for l in all_listings if l.source == "vuokraovi"]
    # sato_ids = [l.external_id for l in all_listings if l.source == "sato"]

    deactivated_v = await service.deactivate_missing(vuokraovi_ids, source="vuokraovi")
    # deactivated_s = await service.deactivate_missing(sato_ids, source="sato")

    return {
        "parsed": len(all_listings),
        "new": new_count,
        "deactivated": deactivated_v
    }

@router.get("/", response_model=list[ListingRead])
async def get_listings(
    session: AsyncSession = Depends(db_helper.session_getter),
    price_min: Optional[float] = Query(None, description="Минимальная цена €/мес"),
    price_max: Optional[float] = Query(None, description="Максимальная цена €/мес"),
    area_min: Optional[float] = Query(None, description="Минимальная площадь м²"),
    area_max: Optional[float] = Query(None, description="Максимальная площадь м²"),
    district: Optional[str] = Query(None, description="Район, например Kallio"),
    room_count: Optional[str] = Query(None, description="ONE_ROOM / TWO_ROOMS / THREE_ROOMS"),
    water_included: Optional[bool] = Query(None, description="Вода включена в аренду"),
    is_private_lessor: Optional[bool] = Query(None, description="True = частник, False = компания"),
    source: Optional[str] = Query(None, description="vuokraovi / sato"),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
):
    """Возвращает список объявлений с фильтрами."""
    service = ListingService(session)
    return await service.get_listings(
        price_min=price_min,
        price_max=price_max,
        area_min=area_min,
        area_max=area_max,
        district=district,
        room_count=room_count,
        water_included=water_included,
        is_private_lessor=is_private_lessor,
        source=source,
        limit=limit,
        offset=offset,
    )