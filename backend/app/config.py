import os
import secrets
import logging
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_PATH = BASE_DIR / "database" / "agenda.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

logger = logging.getLogger(__name__)

# JWT secret from .env or environment variable
# SECURITY: Must be at least 32 bytes (256 bits) for HS256
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    JWT_SECRET = secrets.token_urlsafe(64)
    logger.warning("JWT_SECRET not set. Using random secret. Tokens will not persist across restarts.")
else:
    # Validate minimum entropy
    if len(JWT_SECRET) < 32:
        raise ValueError(
            f"JWT_SECRET must be at least 32 bytes. Current: {len(JWT_SECRET)} bytes. "
            f"Generate with: openssl rand -hex 32"
        )

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
