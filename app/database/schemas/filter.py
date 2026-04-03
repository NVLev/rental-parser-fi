from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserFilterBase(BaseModel):
    source: str = "both"

    price_min: Optional[float] = None
    price_max: Optional[float] = None

    area_min: Optional[float] = None
    area_max: Optional[float] = None

    districts: Optional[str] = Field(None, description="Районы через запятую: Kallio,Kamppi")
    room_counts: Optional[str] = Field(None, description="ONE_ROOM,TWO_ROOMS,THREE_ROOMS")

    water_included_only: bool = False


class UserFilterCreate(UserFilterBase):
    user_id: int


class UserFilterRead(UserFilterBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True