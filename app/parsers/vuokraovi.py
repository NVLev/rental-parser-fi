import asyncio
from typing import List, Dict
from datetime import datetime

import httpx

from config import settings
from app.database.models import Listing


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
        self.municipality_code = settings.vuokraovi.municipality_code
        self.delay = settings.parser.request_delay_seconds
        self.client = httpx.AsyncClient()

    async def fetch_page(self, offset: int = 0) -> Dict:
        url = f"{self.base_url}/v3/announcements/rental/search/listpage"

        payload = {
            "locationSearchCriteria": {
                "municipalityCodes": [self.municipality_code]
            },
            "pagination": {
                "firstResult": offset
            }
        }


        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    async def fetch_details(self, friendly_id: str) -> Dict:
        url = f"{self.base_url}/v3/announcement/rental/details"

        params = {"friendlyId": friendly_id}


        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def map_to_model(self, item: dict) -> Listing:
        friendly_id = item["friendlyId"]

        def parse_datetime(value: str | None) -> datetime | None:
            if not value:
                return None
            return datetime.fromisoformat(value.replace("Z", "+00:00"))

        return Listing(
            external_id=friendly_id,
            source="vuokraovi",
            url=f"https://www.vuokraovi.com/en/item/{friendly_id}",

            price=float(item.get("searchRent") or 0),
            area=item.get("area"),
            district=item.get("addressLine2"),
            address=item.get("addressLine1"),

            room_count=item.get("roomCount"),
            room_structure=item.get("roomStructure"),

            published_at=parse_datetime(item.get("publishingTime")),
        )





    def is_sato_listing(self, item: Dict) -> bool:
        return item.get("customerGroupId") == settings.vuokraovi.sato_customer_group_id

    async def parse(self) -> List[Listing]:
        results: List[Listing] = []

        offset = 0
        limit = settings.parser.max_listings_per_run

        while len(results) < limit:
            data = await self.fetch_page(offset)

            raw_items = data.get("announcements", [])

            if not raw_items:
                break

            filtered_items = [
                item for item in raw_items
                if not self.is_sato_listing(item)
            ]


            for item in filtered_items:
                model = self.map_to_model(item)
                if not model:
                    continue
                results.append(model)

                if len(results) >= limit:
                    break

            offset += len(raw_items)

            await asyncio.sleep(self.delay)

        return results

    async def close(self):
        await self.client.aclose()