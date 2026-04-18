from datetime import datetime

from pydantic import BaseModel


class SeenListingRead(BaseModel):
    id: int
    user_id: int
    listing_id: int
    notified_at: datetime

    class Config:
        from_attributes = True
