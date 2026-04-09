import asyncio
import logging
from typing import List, Dict, Optional

import httpx

from config import settings
from app.database.models import Listing

logger = logging.getLogger(__name__)


class SatoParser:
    def __init__(self):
        self.url = "https://oma.sato.fi/api/realestates/v2/product/searchV2?lang=en"
        self.delay = settings.parser.request_delay_seconds
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=15.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def fetch_page(self, offset: int = 0) -> Dict:
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
            "page": {"fromIndex": offset, "pageSize": 25},
        }

        response = await self.client.post(self.url, json=payload)
        response.raise_for_status()
        return response.json()

    def map_to_listing(self, item: Dict) -> Listing:
        apt = item["apartment"]

        return Listing(
            external_id=apt["apartmentId"],
            source="sato",
            url=f"https://www.sato.fi/en/apartment/{apt['apartmentId']}",  # временно

            price=apt["rent"]["normal"]["value"],
            area=apt.get("livingArea", {}).get("value"),

            address=apt.get("name"),
            room_structure=apt.get("rooms", {}).get("formatted"),

            water_included=(
                apt.get("waterCharge", {}).get("type") == "INCLUDED_IN_RENT"
            ),

            electricity_included=apt.get("flags", {}).get("electricityIncludedInRent"),

            is_private_lessor=False,
        )

    async def parse(self) -> List[Listing]:
        if not self.client:
            raise RuntimeError("Use as async context manager")

        results: List[Listing] = []
        offset = 0
        limit = settings.parser.max_listings_per_run

        while len(results) < limit:
            data = await self.fetch_page(offset)
            items = data.get("products", {}).get("content", [])

            if not items:
                break

            for item in items:
                listing = self.map_to_listing(item)
                results.append(listing)

                if len(results) >= limit:
                    break

            offset += len(items)
            await asyncio.sleep(self.delay)

        logger.info("SatoParser: collected %d listings", len(results))
        return results