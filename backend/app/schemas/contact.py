from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import datetime
import re


def validate_url(value: str | None, field_name: str) -> str | None:
    """Validate URL starts with http:// or https://"""
    if value is None:
        return None
    if not value.startswith(('http://', 'https://')):
        raise ValueError(f'{field_name} debe comenzar con http:// o https://')
    return value


def validate_phone(value: str) -> str:
    """Validate phone contains only digits, spaces, dashes, parentheses"""
    if not re.match(r'^[\d\s\-\(\)]+$', value):
        raise ValueError('El teléfono solo puede contener números, espacios, guiones y paréntesis')
    return value


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=6, max_length=20)
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
        return validate_phone(v)

    @field_validator('website')
    @classmethod
    def validate_website_field(cls, v):
        return validate_url(v, 'website')

    @field_validator('maps_url')
    @classmethod
    def validate_maps_url_field(cls, v):
        return validate_url(v, 'maps_url')


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


class ContactResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: str | None
    address: str | None
    city: str | None
    neighborhood: str | None
    category_id: int | None
    description: str | None
    user_id: int | None
    schedule: str | None
    website: str | None
    photo_path: str | None
    latitude: float | None
    longitude: float | None
    maps_url: str | None
    is_verified: bool | None
    verified_by: int | None
    verified_at: datetime | None
    pending_changes_count: int | None
    created_at: datetime | None
    updated_at: datetime | None

    class Config:
        from_attributes = True


class ContactHistoryResponse(BaseModel):
    id: int
    contact_id: int
    user_id: int | None
    field_name: str
    old_value: str | None
    new_value: str | None
    changed_at: datetime | None

    class Config:
        from_attributes = True


class VerifyContactRequest(BaseModel):
    is_verified: bool = True


class ContactChangeCreate(BaseModel):
    field_name: str
    new_value: str


class ContactChangeResponse(BaseModel):
    id: int
    contact_id: int
    user_id: int | None
    field_name: str
    old_value: str | None
    new_value: str
    is_verified: bool
    verified_by: int | None
    verified_at: datetime | None
    created_at: datetime | None

    class Config:
        from_attributes = True
