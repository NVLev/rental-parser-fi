import asyncio
import logging
from typing import List, Dict, Optional

import httpx

from config import settings
from app.database.models import Listing

logger = logging.getLogger(__name__)

ROOM_COUNT_MAP = {
    "TYPE_FLATSHARE": "ONE_ROOM",
    "TYPE_1H": "ONE_ROOM",
    "TYPE_2H": "TWO_ROOMS",
    "TYPE_3H": "THREE_ROOMS",
    "TYPE_4H": "FOUR_ROOMS",
    "TYPE_5H": "FOUR_ROOMS",  # у нас нет FIVE_ROOMS в enum
}

IMAGE_BASE_URL = "https://d1fzpuekdrhqpx.cloudfront.net/{id}?w=1280&h=854&fit=crop&q=80"


class SatoParser:
    SEARCH_URL = "https://oma.sato.fi/api/realestates/v2/product/searchV2?lang=en"
    DETAIL_URL = "https://oma.sato.fi/api/realestates/v2/real-estate/{real_estate_id}/apartments?status=FREE,GOING_TO_BE_FREE&lang=en"

    def __init__(self):
        self.delay = settings.parser.request_delay_seconds
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=15.0,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
                "Origin": "https://www.sato.fi",
                "x-requested-with": "XMLHttpRequest",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def fetch_search_page(self, offset: int = 0) -> Dict:
        payload = {
            "sort": {"id": "RELEASE", "field": "VACANCY", "descending": False},
            "rules": [
                {
                    "field": "REGION",
                    "operator": "EQUAL",
                    "value": {
                        "municipality": "Helsinki",
                        "district": None,
                        "zip": None,
                        "address": None,
                    },
                }
            ],
            "page": {"fromIndex": offset, "pageSize": 27},
        }
        response = await self.client.post(self.SEARCH_URL, json=payload)
        response.raise_for_status()
        return response.json()

    async def fetch_real_estate_apartments(self, real_estate_id: str) -> List[Dict]:
        url = self.DETAIL_URL.format(real_estate_id=real_estate_id)
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("content", [])

    @staticmethod
    def _get_floor_plan_url(media_assets: List[Dict]) -> Optional[str]:
        for asset in media_assets:
            if asset.get("type") == "FLOORPLAN":
                return IMAGE_BASE_URL.format(id=asset["id"])
        return None

    @staticmethod
    def _get_district(apt: Dict) -> Optional[str]:
        """Район из маркетинговых данных или адреса."""
        # Пробуем marketing — там бывает название района в HEADER
        for block in apt.get("marketing", []):
            for item in block.get("items", []):
                if item.get("type") == "HEADER":
                    text = item.get("text", "")
                    if text:
                        return text  # напр. "Spacious homes..." — не идеально, но лучше null
        # addresses[0].district тоже часто null у SATO
        addresses = apt.get("addresses", [])
        if addresses:
            return addresses[0].get("district")
        return None

    @staticmethod
    def _get_available_from(apt: Dict) -> Optional[str]:
        available = apt.get("state", {}).get("available")
        if available:
            return available  # "2026-05-01" или null
        status = apt.get("state", {}).get("status")
        if status == "FREE":
            return "IMMEDIATELY"
        return None

    @staticmethod
    def _build_address(apt: Dict) -> Optional[str]:
        addresses = apt.get("addresses", [])
        if not addresses:
            return apt.get("name")
        addr = addresses[0]
        street = addr.get("streetAddress", "")
        staircase = addr.get("staircase", "")
        apt_num = addr.get("apartmentNumber", "")
        floor_info = addr.get("floor", {}) or {}
        floor = floor_info.get("number", "")

        parts = [street]
        if staircase:
            parts.append(staircase)
        result = " ".join(filter(None, parts))
        if apt_num:
            result += f" apt.{apt_num}"
        if floor:
            result += f" (floor {floor}/{floor_info.get('total', '')})"
        return result or apt.get("name")

    def map_to_listing(self, apt: Dict, product_id: str) -> Listing:
        water_charge = apt.get("waterCharge", {}) or {}
        water_type = water_charge.get("type")  # INCLUDED_IN_RENT | PER_PERSON | null
        water_included = water_type == "INCLUDED_IN_RENT"
        water_price = None
        if not water_included and water_charge.get("amount"):
            water_price = water_charge["amount"].get("value")

        rooms = apt.get("rooms", {}) or {}
        room_type = rooms.get("type")  # TYPE_1H, TYPE_2H, ...
        room_count = ROOM_COUNT_MAP.get(room_type)

        available_from = self._get_available_from(apt)
        floor_plan_url = self._get_floor_plan_url(apt.get("mediaAssets", []))
        address = self._build_address(apt)

        return Listing(
            external_id=apt["apartmentId"],
            source="sato",
            url=f"https://www.sato.fi/en/apartment/{product_id}",
            price=apt["rent"]["normal"]["value"],
            area=apt.get("livingArea", {}).get("value"),
            address=address,
            district=apt.get("addresses", [{}])[0].get("district") if apt.get("addresses") else None,
            room_count=room_count,
            room_structure=rooms.get("formatted"),
            water_included=water_included,
            water_price=water_price,
            electricity_included=apt.get("flags", {}).get("electricityIncludedInRent"),
            floor_plan_url=floor_plan_url,
            available_from=available_from,
            is_private_lessor=False,
            lessor_name="SATO",
        )

    async def parse(self) -> List[Listing]:
        if not self.client:
            raise RuntimeError("Use as async context manager")

        results: List[Listing] = []
        limit = settings.parser.max_listings_per_run
        offset = 0

        while len(results) < limit:
            search_data = await self.fetch_search_page(offset)
            products = search_data.get("products", {})
            items = products.get("content", [])

            if not items:
                break

            for item in items:
                real_estate_id = item["id"]
                product_id = item["apartment"]["productId"]

                try:
                    apartments = await self.fetch_real_estate_apartments(real_estate_id)
                    await asyncio.sleep(self.delay)
                except Exception as e:
                    logger.warning("Failed to fetch apartments for %s: %s", real_estate_id, e)
                    continue

                for apt in apartments:
                    listing = self.map_to_listing(apt, product_id)
                    results.append(listing)

                if len(results) >= limit:
                    break

            total = products.get("totalElements", 0)
            offset += len(items)
            if offset >= total:
                break

        logger.info("SatoParser: collected %d listings", len(results))
        return results