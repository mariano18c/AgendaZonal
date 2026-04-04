from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator
from datetime import datetime
import re
import html


def validate_url(value: str | None, field_name: str) -> str | None:
    """Validate URL starts with http:// or https://"""
    if value is None:
        return None
    if not value.startswith(('http://', 'https://')):
        raise ValueError(f'{field_name} debe comenzar con http:// o https://')
    return value


def validate_phone(value: str | None) -> str | None:
    """Validate phone contains only digits, spaces, dashes, parentheses"""
    if value is None or value.strip() == '':
        return None
    if not re.match(r'^[\d\s\-\(\)]+$', value):
        raise ValueError('El teléfono solo puede contener números, espacios, guiones y paréntesis')
    return value


def sanitize_text(value: str | None) -> str | None:
    """Escape HTML entities to prevent XSS attacks.

    Uses html.escape to convert <, >, &, " to their HTML entities.
    This ensures user input is safe when rendered in browsers.
    """
    if value is None:
        return None
    # Escape HTML special characters
    sanitized = html.escape(value, quote=True)
    return sanitized


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    address: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    neighborhood: str | None = Field(None, max_length=100)
    category_id: int | None = None
    description: str | None = Field(None, max_length=500)
    schedule: str | None = Field(None, max_length=200)
    website: str | None = Field(None, max_length=255)
    photo_path: str | None = Field(None, max_length=500)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    maps_url: str | None = Field(None, max_length=500)
    instagram: str | None = Field(None, max_length=100)
    facebook: str | None = Field(None, max_length=255)
    about: str | None = Field(None, max_length=2000)

    @field_validator('phone')
    @classmethod
    def validate_phone_field(cls, v):
        return validate_phone(v)

    @field_validator('website')
    @classmethod
    def validate_website_field(cls, v):
        return validate_url(v, 'website')

    @field_validator('maps_url')
    @classmethod
    def validate_maps_url_field(cls, v):
        return validate_url(v, 'maps_url')

    @field_validator('name', 'address', 'city', 'neighborhood', 'description', 'schedule')
    @classmethod
    def sanitize_text_fields(cls, v):
        return sanitize_text(v)


class ContactUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    phone: str | None = Field(None, min_length=6, max_length=20)
    email: EmailStr | None = None
    address: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    neighborhood: str | None = Field(None, max_length=100)
    category_id: int | None = None
    description: str | None = Field(None, max_length=500)
    schedule: str | None = Field(None, max_length=200)
    website: str | None = Field(None, max_length=255)
    photo_path: str | None = Field(None, max_length=500)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    maps_url: str | None = Field(None, max_length=500)

    @field_validator('phone')
    @classmethod
    def validate_phone_field(cls, v):
        if v is not None:
            return validate_phone(v)
        return v

    @field_validator('website')
    @classmethod
    def validate_website_field(cls, v):
        return validate_url(v, 'website')

    @field_validator('maps_url')
    @classmethod
    def validate_maps_url_field(cls, v):
        return validate_url(v, 'maps_url')

    @field_validator('name', 'address', 'city', 'neighborhood', 'description', 'schedule')
    @classmethod
    def sanitize_text_fields(cls, v):
        return sanitize_text(v)


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    neighborhood: str | None = None
    category_id: int | None = None
    description: str | None = None
    user_id: int | None = None
    schedule: str | None = None
    website: str | None = None
    photo_path: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    maps_url: str | None = None
    is_verified: bool | None = None
    verified_by: int | None = None
    verified_at: datetime | None = None
    verification_level: int | None = 0
    status: str | None = "active"
    avg_rating: float | None = 0
    review_count: int | None = 0
    pending_changes_count: int | None = None
    instagram: str | None = None
    facebook: str | None = None
    about: str | None = None
    slug: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Campo opcional para geo search
    distance_km: float | None = None
    # Campos calculados (no en DB)
    photos: list | None = None
    schedules: list | None = None
    is_open_now: bool | None = None


class ContactHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contact_id: int
    user_id: int | None = None
    field_name: str
    old_value: str | None = None
    new_value: str | None = None
    changed_at: datetime | None = None


class VerifyContactRequest(BaseModel):
    is_verified: bool = True


class ContactChangeCreate(BaseModel):
    field_name: str
    new_value: str

    @field_validator('new_value')
    @classmethod
    def sanitize_new_value(cls, v):
        return sanitize_text(v)


class ContactChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contact_id: int
    user_id: int | None = None
    field_name: str
    old_value: str | None = None
    new_value: str
    is_verified: bool
    verified_by: int | None = None
    verified_at: datetime | None = None
    created_at: datetime | None = None
