from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    phone_area_code: str = Field(min_length=2, max_length=5)
    phone_number: str = Field(min_length=6, max_length=15)
    password: str = Field(min_length=8, max_length=100)


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    phone_area_code: str
    phone_number: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    token: str
    user: UserResponse
