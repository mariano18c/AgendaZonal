"""Unit tests — JWT auth logic."""
import pytest
import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from app.auth import create_token, verify_token
from app.config import JWT_SECRET, JWT_ALGORITHM


class TestCreateToken:
    def test_returns_string(self):
        t = create_token(1)
        assert isinstance(t, str)

    def test_decodable(self):
        t = create_token(42)
        payload = pyjwt.decode(t, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == "42"

    def test_has_expiration(self):
        t = create_token(1)
        payload = pyjwt.decode(t, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert "exp" in payload
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert exp > datetime.now(timezone.utc)

    def test_different_users_different_tokens(self):
        assert create_token(1) != create_token(2)


class TestVerifyToken:
    def test_valid(self):
        t = create_token(1)
        payload = verify_token(t)
        assert payload["sub"] == "1"

    def test_expired_raises(self):
        t = pyjwt.encode(
            {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
            JWT_SECRET, algorithm=JWT_ALGORITHM,
        )
        with pytest.raises(pyjwt.ExpiredSignatureError):
            verify_token(t)

    def test_wrong_secret_raises(self):
        t = pyjwt.encode(
            {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong_secret", algorithm=JWT_ALGORITHM,
        )
        with pytest.raises(pyjwt.InvalidTokenError):
            verify_token(t)

    def test_garbage_raises(self):
        with pytest.raises(pyjwt.DecodeError):
            verify_token("not.a.jwt")
