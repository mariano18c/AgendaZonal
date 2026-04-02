from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
import html


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(None, max_length=500)

    @field_validator('comment')
    @classmethod
    def sanitize_comment(cls, v):
        if v is None:
            return None
        return html.escape(v, quote=True)


class ReviewReplyCreate(BaseModel):
    reply_text: str = Field(min_length=1, max_length=500)

    @field_validator('reply_text')
    @classmethod
    def sanitize_reply(cls, v):
        return html.escape(v, quote=True)


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contact_id: int
    user_id: int
    rating: int
    comment: str | None = None
    photo_path: str | None = None
    is_approved: bool
    approved_by: int | None = None
    approved_at: datetime | None = None
    created_at: datetime | None = None
    # Extra fields (populated by endpoint)
    username: str | None = None
    # Reply fields
    reply_text: str | None = None
    reply_at: datetime | None = None
    reply_by_username: str | None = None


class ReviewListResponse(BaseModel):
    reviews: list[ReviewResponse]
    total: int
    avg_rating: float


class VerifyLevelRequest(BaseModel):
    verification_level: int = Field(ge=0, le=3)
