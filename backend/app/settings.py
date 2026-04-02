"""Pydantic Settings — centralized configuration via environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_path: str = "backend/database/agenda.db"
    database_url: str = ""

    # JWT
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # CORS
    allowed_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    # App
    debug: bool = False
    upload_max_size_mb: int = 5
    max_pending_changes: int = 3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
