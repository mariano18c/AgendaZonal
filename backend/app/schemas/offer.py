from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class OfferCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    discount_pct: int | None = Field(None, ge=1, le=99)
    expires_at: datetime


class OfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contact_id: int
    title: str
    description: str | None = None
    discount_pct: int | None = None
    expires_at: datetime
    is_active: bool
    created_at: datetime | None = None
