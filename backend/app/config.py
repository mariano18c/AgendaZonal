import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_PATH = BASE_DIR / "database" / "agenda.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# JWT secret from .env or environment variable
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    JWT_SECRET = secrets.token_urlsafe(64)
    print(f"WARNING: JWT_SECRET not set. Using random secret. Tokens will not persist across restarts.")

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
