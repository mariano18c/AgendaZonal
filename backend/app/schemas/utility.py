from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class UtilityItemCreate(BaseModel):
    type: str = Field(default="otro", max_length=20)
    name: str = Field(..., min_length=1, max_length=200)
    address: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=20)
    schedule: str | None = Field(None, max_length=200)
    lat: float | None = None
    lon: float | None = None
    city: str | None = Field(None, max_length=100)
    is_priority: bool = False
    notification_message: str | None = Field(None, max_length=200)


class UtilityItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    name: str
    address: str | None = None
    phone: str | None = None
    schedule: str | None = None
    lat: float | None = None
    lon: float | None = None
    city: str | None = None
    is_priority: bool
    is_active: bool
    created_at: datetime | None = None
