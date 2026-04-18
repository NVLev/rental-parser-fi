from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ListingBase(BaseModel):
    price: float
    area: Optional[float] = None
    district: Optional[str] = None
    address: Optional[str] = None

    room_count: Optional[str] = None
    room_structure: Optional[str] = None

    water_included: Optional[bool] = None
    water_price: Optional[float] = None
    electricity_included: Optional[bool] = None

    floor_plan_url: Optional[str] = None
    available_from: Optional[str] = None
    published_at: Optional[datetime] = None

    lessor_name: Optional[str] = None
    is_private_lessor: Optional[bool] = None


class ListingCreate(ListingBase):
    external_id: str
    source: str
    url: str


class ListingRead(ListingBase):
    id: int
    external_id: str
    source: str
    url: str
    scraped_at: datetime
    is_active: bool

    class Config:
        from_attributes = True
