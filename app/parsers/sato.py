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
    "TYPE_5H": "FOUR_ROOMS",
    "TYPE_5H_PLUS": "FOUR_ROOMS",
}

IMAGE_BASE_URL = "https://d1fzpuekdrhqpx.cloudfront.net/{id}?w=1280&h=854&fit=crop&q=80"

MUNICIPALITIES = ["Helsinki", "Espoo", "Vantaa"]

class SatoParser:
    SEARCH_URL = "https://oma.sato.fi/api/realestates/v2/product/searchV2?lang=en"

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

    async def fetch_page(self, offset: int = 0, municipality: str = "Helsinki") -> Dict:
        payload = {
            "sort": {"id": "RELEASE", "field": "VACANCY", "descending": False},
            "rules": [
                {
                    "field": "REGION",
                    "operator": "EQUAL",
                    "value": {
                        "municipality": municipality,
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

    @staticmethod
    def _get_floor_plan_url(media_assets: List[Dict]) -> Optional[str]:
        for asset in media_assets:
            if asset.get("type") == "FLOORPLAN":
                return IMAGE_BASE_URL.format(id=asset["id"])
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
        floor_info = addr.get("floor") or {}
        floor = floor_info.get("number", "")
        total = floor_info.get("total", "")

        result = " ".join(filter(None, [street, staircase]))
        if apt_num:
            result += f" apt.{apt_num}"
        if floor:
            result += f" (floor {floor}/{total})"
        return result or apt.get("name")

    def map_to_listing(self, item: Dict) -> Listing:
        apt = item["apartment"]
        real_estate = item["realEstate"]

        # district из realEstate
        district = None
        re_addresses = real_estate.get("addresses", [])
        if re_addresses and re_addresses[0].get("district"):
            district = re_addresses[0]["district"]["name"]

        # available_from
        available = apt.get("state", {}).get("available")
        if available:
            available_from = available  # "2026-05-01"
        elif apt.get("state", {}).get("status") == "FREE":
            available_from = "IMMEDIATELY"
        else:
            available_from = None

        # water
        water_charge = apt.get("waterCharge") or {}
        water_included = water_charge.get("type") == "INCLUDED_IN_RENT"
        water_price = None
        if not water_included and water_charge.get("amount"):
            water_price = water_charge["amount"].get("value")

        # room_count
        room_count = ROOM_COUNT_MAP.get(apt.get("rooms", {}).get("type"))

        # url
        municipality = ""
        street_for_url = ""
        if re_addresses:
            municipality = re_addresses[0].get("municipality", {}).get("name", "helsinki").lower()
            street_for_url = re_addresses[0].get("streetAddress", "").lower().replace(" ", "%20")
        district_for_url = district.lower().replace(" ", "-") if district else ""
        url = (
            f"https://www.sato.fi/en/rental-apartments"
            f"/{municipality}/{district_for_url}/{street_for_url}"
            f"/{real_estate['id']}/apartment/{item['id']}"
        )

        return Listing(
            external_id=apt["apartmentId"],
            source="sato",
            url=url,
            price=apt["rent"]["normal"]["value"],
            area=apt.get("livingArea", {}).get("value"),
            address=self._build_address(apt),
            district=district,
            room_count=room_count,
            room_structure=apt.get("rooms", {}).get("formatted"),
            water_included=water_included,
            water_price=water_price,
            electricity_included=apt.get("flags", {}).get("electricityIncludedInRent"),
            floor_plan_url=self._get_floor_plan_url(apt.get("mediaAssets", [])),
            available_from=available_from,
            is_private_lessor=False,
            lessor_name="SATO",
        )

    async def parse(self) -> List[Listing]:
        if not self.client:
            raise RuntimeError("Use as async context manager")

        results: List[Listing] = []

        for municipality in MUNICIPALITIES:
            offset = 0
            municipality_count = 0
            logger.info("SatoParser: fetching %s", municipality)

            while True:
                data = await self.fetch_page(offset, municipality)
                products = data.get("products", {})
                items = products.get("content", [])
                total = products.get("totalElements", 0)

                if not items:
                    break

                for item in items:
                    listing = self.map_to_listing(item)
                    results.append(listing)
                    municipality_count += 1

                logger.info("SatoParser: %s — %d/%d", municipality, municipality_count, total)

                offset += len(items)
                if offset >= total:
                    break

                await asyncio.sleep(self.delay)
        print("SatoParser: total collected %d listings", len(results))
        logger.info("SatoParser: total collected %d listings", len(results))
        return results