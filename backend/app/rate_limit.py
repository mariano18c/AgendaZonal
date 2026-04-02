"""Shared rate limiter instance."""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

# Default rate limits for API endpoints
DEFAULT_RATE_LIMIT = "60/minute"
SEARCH_RATE_LIMIT = "30/minute"
AUTH_RATE_LIMIT = "10/minute"

# Disable rate limiting during tests
if os.getenv("TESTING") == "1":
    limiter = Limiter(key_func=get_remote_address, enabled=False)
else:
    limiter = Limiter(key_func=get_remote_address, default_limits=[DEFAULT_RATE_LIMIT])
