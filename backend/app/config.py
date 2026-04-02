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

# ---------------------------------------------------------------------------
# VAPID Keys for Web Push Notifications
# ---------------------------------------------------------------------------
# Generate once with:
#   python -c "from pywebpush import vapid; keys = vapid.generate_vapid_key_pair(); print('Private:', keys[0]); print('Public:', keys[1])"
#
# Store in .env as:
#   VAPID_PRIVATE_KEY=<private_key>
#   VAPID_PUBLIC_KEY=<public_key>
#   VAPID_CLAIM_EMAIL=mailto:admin@tudominio.com
# ---------------------------------------------------------------------------

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_CLAIM_EMAIL = os.getenv("VAPID_CLAIM_EMAIL", "mailto:admin@agendazonal.local")

if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
    logger.warning(
        "VAPID keys not configured. Push notifications will not work. "
        "Generate with: python -c \"from pywebpush import vapid; "
        "keys = vapid.generate_vapid_key_pair(); "
        "print('VAPID_PRIVATE_KEY=' + keys[0]); "
        "print('VAPID_PUBLIC_KEY=' + keys[1])\""
    )
