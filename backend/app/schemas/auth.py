from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CaptchaChallengeResponse(BaseModel):
    """Response containing a CAPTCHA challenge."""
    challenge_id: str
    question: str


class CaptchaVerifyRequest(BaseModel):
    """Request to verify a CAPTCHA answer."""
    challenge_id: str
    answer: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    phone_area_code: str = Field(min_length=2, max_length=5)
    phone_number: str = Field(min_length=6, max_length=15)
    password: str = Field(min_length=8, max_length=100)
    captcha_challenge_id: str = ""
    captcha_answer: str = ""


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    phone_area_code: str
    phone_number: str
    role: str
    is_active: bool


class AuthResponse(BaseModel):
    token: str
    user: UserResponse
