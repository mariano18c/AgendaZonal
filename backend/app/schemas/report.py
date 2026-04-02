from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
import html


class ReportCreate(BaseModel):
    reason: str = Field(..., pattern="^(spam|falso|inapropiado|cerrado)$")
    details: str | None = Field(None, max_length=500)

    @field_validator('details')
    @classmethod
    def sanitize_details(cls, v):
        if v is None:
            return None
        return html.escape(v, quote=True)


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contact_id: int
    user_id: int
    reason: str
    details: str | None = None
    is_resolved: bool
    resolved_by: int | None = None
    resolved_at: datetime | None = None
    created_at: datetime | None = None
