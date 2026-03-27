from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    phone_area_code: str = Field(min_length=2, max_length=5)
    phone_number: str = Field(min_length=6, max_length=15)
    password: str = Field(min_length=8, max_length=100)
    role: str = 'user'  # user, moderator, admin


class UserUpdate(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=50)
    email: EmailStr | None = None
    phone_area_code: str | None = Field(None, min_length=2, max_length=5)
    phone_number: str | None = Field(None, min_length=6, max_length=15)
    password: str | None = Field(None, min_length=8, max_length=100)
    role: str | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    phone_area_code: str
    phone_number: str
    role: str
    is_active: bool
    deactivated_at: datetime | None
    deactivated_by: int | None
    created_at: datetime | None

    class Config:
        from_attributes = True


class UserRoleUpdate(BaseModel):
    role: str  # user, moderator, admin


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=8, max_length=100)
