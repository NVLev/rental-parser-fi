import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
import re
import httpx

from config import settings
from app.database.models import Listing

logger = logging.getLogger(__name__)


WATER_INCLUDED_RE = re.compile(
    r"vesi\s*(sisältyy|kuuluu)\s*vuokraan"
    r"|water\s*is\s*available\s*for\s*rent"
    r"|vesimaksu\s*sisältyy\s*vuokraan|"
    r"vesi-?\s*ja\s*lämmityskulut|"
    r"|kulutukseen\s*perustuva\s*vesimaksu",

    re.IGNORECASE,
)
WATER_NOT_INCLUDED_RE = re.compile(
    r"vesimaksu[\s:–\-]*\d"
    r"|vesiennakkomaksu"
    r"vesimaksuennakko\s*\d"
    r"vesimaksu\s*\d"
    r"\d+\s*e.*vesi"
    r"|vesi[\s:]*kulutuksen\s*mukaan",
    re.IGNORECASE,
)
ELEC_INCLUDED_RE = re.compile(
    r"sähkö\s*(sisältyy|kuuluu)\s*vuokraan"
    r"|sähkösopimus\w*[\s:]*sisältyy"  
    r"|sähkö-?\s*.*?lämmityskulut"
    r"|electricity\s*included",
    re.IGNORECASE,
)
ELEC_NOT_INCLUDED_RE = re.compile(
    r"vuokralainen\s*tekee\s*(oman\s*)?sähkösopimuksen"
    r"|sähkösopimus[\s:]*vuokralainen\s*tekee"
    r"|omalla\s*(sähkö)?sopimuksella"
    r"|sähkö\s*kulutuksen\s*mukaan"
    r"|kulutuksen\s*mukaan\s*sähkö"
    r"|tenant\s*makes.*electricity",
    re.IGNORECASE,
)

class VuokraoviParser:
    """
        Парсер объявлений аренды с сайта Vuokraovi.

        Использует публичный REST API Vuokraovi для получения списка объявлений
        и (при необходимости) деталей.

        Основные задачи:
        - загрузка страниц с объявлениями (пагинация)
        - фильтрация нерелевантных объявлений (например, SATO)
        - преобразование ответа API в модель Listing (ORM)

        Особенности:
        - асинхронная работа через httpx
        - учитывает настройки из config (лимиты, задержки, регион)
        - не содержит логики сохранения в БД (это уровень service)

        Использование:
            parser = VuokraoviParser()
            listings = await parser.parse()
        """
    def __init__(self):
        self.base_url = settings.vuokraovi.base_url
        self.municipality_codes = settings.vuokraovi.municipality_codes
        self.delay = settings.parser.request_delay_seconds
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "VuokraoviParser":
        self.client = httpx.AsyncClient(timeout=15.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
        if exc_type:
            logger.error("VuokraoviParser exited with error: %s: %s", exc_type.__name__, exc_val)
        return False

    async def close(self) -> None:
        if self.client and not self.client.is_closed:
            await self.client.aclose()
            logger.debug("httpx client closed")

    def _build_location_terms(self, code: str, name: str) -> List[Dict]:
        return [
            {
                "type": "CITY",
                "code": code,
                "shortName": name,
                "parentCountryCode": "FI",
                "parentRegionCode": "FI_UUSIMAA",
                "parentRegionName": "Uusimaa",
                "fullName": name,
                "classified": True,
            }
        ]

    async def fetch_page(self, offset: int, code: str, name: str) -> Dict:
        url = f"{self.base_url}/v3/announcements/rental/search/listpage"

        payload = {
            "locationSearchCriteria": {
                "classifiedLocationTerms": self._build_location_terms(code, name),
                "unclassifiedLocationTerms": [],
            },
            "lessorType": "ALL",
            "publishingTimeSearchCriteria": "ANY_DAY",
            "officeIds": None,
            "rentMin": None,
            "rentMax": None,
            "checkIfHasImages": None,
            "checkIfHasPanorama": None,
            "checkIfHasVideo": None,
            "checkIfHasShowingWithinSevenDays": None,
            "pagination": {
                "sortingOrder": {
                    "property": "PUBLISHED_OR_UPDATED_AT",
                    "direction": "DESC",
                },
                "firstResult": offset,
                "maxResults": 25,
                "page": (offset // 25) + 1,
            },
            "propertyType": "RESIDENTIAL",
            "freeTextSearch": "",
            "residentialPropertyTypes": [],
            "roomCounts": None,
            "sizeMin": None,
            "sizeMax": None,
            "overallConditions": None,
            "yearMin": None,
            "yearMax": None,
            "rentalAgreements": None,
            "rentalAvailabilities": None,
            "kitchenTypes": None,
            "livingFormTypes": [],
            "newBuildingSearchCriteria": "ALL_PROPERTIES",
        }

        logger.info(f"payload: {payload}")
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        logger.info("fetch_page offset=%d: countOfAllResults=%s, announcements=%d",
                    offset,
                    data.get("countOfAllResults"),
                    len(data.get("announcements", [])))
        return data

    async def fetch_details(self, friendly_id: str) -> Dict:
        url = f"{self.base_url}/v3/announcement/rental/details"
        try:
            response = await self.client.get(url, params={"friendlyId": friendly_id})
            response.raise_for_status()
            logger.debug("Fetched details for %s", friendly_id)
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning("Failed to fetch details for %s: HTTP %s", friendly_id, e.response.status_code)
            return None
        except httpx.RequestError as e:
            logger.warning("Request error fetching details for %s: %s", friendly_id, e)
            return None

    def is_sato_listing(self, item: Dict) -> bool:
        return (
                item.get("office", {}).get("customerGroupId")
                == settings.vuokraovi.sato_customer_group_id
        )

    def _parse_availability(self, item: Dict) -> Optional[str]:
        availability = item.get("rentalAvailability", {})
        if not availability:
            return None
        if availability.get("type") == "IMMEDIATELY":
            return "IMMEDIATELY"
        return availability.get("vacancyDate")  # "2026-05-01"

    def _parse_water(self, details: Dict) -> Optional[bool]:
        charges = details.get("property", {}).get("periodicCharges", [])
        for charge in charges:
            if charge.get("periodicCharge") == "WATER":
                return charge.get("includedInOverallCost", False)

        # Fallback по тексту
        text_sources = " ".join(filter(None, [
            details.get("property", {}).get("periodicChargesAdditionalInfo"),
            details.get("property", {}).get("description"),
            details.get("text"),
        ]))

        if WATER_NOT_INCLUDED_RE.search(text_sources):
            return False

        if WATER_INCLUDED_RE.search(text_sources):
            return True


        return None

    def _parse_electricity(self, details: Dict) -> Optional[bool]:
        charges = details.get("property", {}).get("periodicCharges", [])
        for charge in charges:
            if charge.get("periodicCharge") == "ELECTRICITY":
                return charge.get("includedInOverallCost", False)

        text_sources = " ".join(filter(None, [
            details.get("property", {}).get("periodicChargesAdditionalInfo"),
            details.get("property", {}).get("description"),
            details.get("text"),
        ]))

        if ELEC_INCLUDED_RE.search(text_sources):
            return True
        if ELEC_NOT_INCLUDED_RE.search(text_sources):
            return False

        return None

    def _parse_price(self, details: Dict) -> Optional[float]:
        # Сначала из periodicCharges
        charges = details.get("property", {}).get("periodicCharges", [])
        for charge in charges:
            if charge.get("periodicCharge") == "WATER":
                included = charge.get("includedInOverallCost", False)
                return charge.get("price") if not included else None

        # Fallback — ищем цену в тексте объявления
        text = (details.get("text") or "").lower()
        info = (details.get("property", {}).get("periodicChargesAdditionalInfo") or "").lower()

        for source in [info, text]:
            match = re.search(r"vesimaksu\s*(\d+[,.]?\d*)\s*€", source)
            if match:
                price_str = match.group(1).replace(",", ".")
                return float(price_str)

        return None


    def _parse_floor_plan_url(self, details: Dict) -> Optional[str]:
        image_ids = details.get("imageIds", {})
        floor_plan_ids = image_ids.get("floorPlanImageIds", [])
        if not floor_plan_ids:
            return None

        first_id = floor_plan_ids[0]
        images = details.get("property", {}).get("images", {})
        image_data = images.get(str(first_id), {})
        uri = image_data.get("image", {}).get("uri")
        if uri:
            return f"https:{uri}".replace("{imageParameters}", "1280x854,fit,q80,f=webp")
        return None

    def _parse_district(self, details: Dict, fallback: Optional[str] = None) -> Optional[str]:
        """Берёт subdistrict из деталей, fallback на addressLine2 из листинга."""
        subdistrict = (
            details.get("property", {})
            .get("subdistrict", {})
            .get("defaultName")
        )
        return subdistrict or fallback

    def _parse_lessor(self, details: Dict) -> tuple[Optional[str], Optional[bool]]:
        """Возвращает (имя арендодателя, является ли частником)."""
        contact = details.get("announcementContactInfo", {})
        is_private = contact.get("isPrivateLessor")
        if is_private:
            name = contact.get("name")
        else:
            name = contact.get("officeName")
        return name, is_private

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            logger.warning("Could not parse datetime: %s", value)
            return None

    def map_to_listing(self, item: Dict, details: Optional[Dict] = None) -> Optional[Listing]:
        friendly_id = item["friendlyId"]

        if details and details.get("status") == "UNPUBLISHED":
            logger.info("Skipping unpublished listing %s", friendly_id)
            return None

        listing = Listing(
            external_id=friendly_id,
            source="vuokraovi",
            url=f"https://www.vuokraovi.com/en/item/{friendly_id}",
            price=float(item.get("searchRent") or 0),
            area=item.get("area"),
            district=item.get("addressLine2"),
            address=item.get("addressLine1"),
            room_count=item.get("roomCount"),
            room_structure=item.get("roomStructure"),
            available_from=self._parse_availability(item),
            published_at=self._parse_datetime(item.get("publishingTime")),
        )

        if details:
            listing.water_included = self._parse_water(details)
            listing.water_price = self._parse_price(details)
            if listing.water_price and listing.water_included is None:
                listing.water_included = False
            listing.electricity_included = self._parse_electricity(details)
            listing.floor_plan_url = self._parse_floor_plan_url(details)
            listing.district = self._parse_district(details, fallback=item.get("addressLine2"))
            listing.lessor_name, listing.is_private_lessor = self._parse_lessor(details)

        return listing

    async def parse(self) -> List[Listing]:
        if not self.client:
            raise RuntimeError("VuokraoviParser must be used as async context manager")

        results: List[Listing] = []
        seen_ids: set[str] = set()
        for code, name in self.municipality_codes:
            logger.info("Start parsing municipality: %s", name)

            offset = 0

            while True:
                try:
                    data = await self.fetch_page(offset, code, name)
                except httpx.HTTPStatusError as e:
                    logger.error(
                        "Failed to fetch %s offset=%d: HTTP %s",
                        name,
                        offset,
                        e.response.status_code,
                    )
                    break
                except httpx.RequestError as e:
                    logger.error(
                        "Request error %s offset=%d: %s",
                        name,
                        offset,
                        e,
                    )
                    break

                raw_items = data.get("announcements", [])
                total = data.get("countOfAllResults", 0)

                if not raw_items:
                    logger.info("No more listings for %s at offset %d", name, offset)
                    break

                filtered = [item for item in raw_items if not self.is_sato_listing(item)]

                logger.info(
                    "%s offset=%d: %d total, %d after SATO filter",
                    name,
                    offset,
                    len(raw_items),
                    len(filtered),
                )

                for item in filtered:
                    friendly_id = item.get("friendlyId")
                    if not friendly_id:
                        continue

                    if friendly_id in seen_ids:
                        continue
                    seen_ids.add(friendly_id)

                    details = await self.fetch_details(friendly_id)
                    await asyncio.sleep(self.delay)

                    listing = self.map_to_listing(item, details)
                    if listing is None:
                        continue

                    results.append(listing)

                offset += 25

                if offset >= total:
                    logger.info("Finished %s (offset %d >= total %d)", name, offset, total)
                    break

        print("VuokraoviParser finished: %d listings collected", len(results))
        logger.info("VuokraoviParser finished: %d listings collected", len(results))
        return results