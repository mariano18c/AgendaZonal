"""Security tests — JWT token security.

Adapted from tests_ant/security/test_jwt_security.py — uses current conftest fixtures.
Covers:
- Expired tokens (rejected, error message)
- Malformed tokens (invalid, empty, missing sub, nonexistent user)
- Algorithm confusion (none, wrong secret, HS384)
- Token tampering (payload tamper, Basic auth scheme)
"""
import uuid
import pytest
import jwt as pyjwt
from datetime import datetime, timedelta, timezone

from app.config import JWT_SECRET, JWT_ALGORITHM, JWT_ISSUER, JWT_AUDIENCE
from app.auth import create_token


def _uid():
    return uuid.uuid4().hex[:8]


class TestExpiredTokens:

    @pytest.mark.security
    def test_expired_token_rejected(self, client):
        expired_payload = {
            "sub": "1",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = pyjwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {expired_token}",
        })
        assert resp.status_code == 401

    @pytest.mark.security
    def test_expired_token_error_message(self, client):
        expired_payload = {
            "sub": "1",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = pyjwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {expired_token}",
        })
        assert resp.status_code == 401
        detail = resp.json()["detail"].lower()
        assert "expirado" in detail or "invalido" in detail or "token" in detail


class TestMalformedTokens:

    @pytest.mark.security
    def test_completely_invalid_token(self, client):
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer not-a-jwt-token-at-all",
        })
        assert resp.status_code == 401

    @pytest.mark.security
    def test_empty_token(self, client):
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer ",
        })
        assert resp.status_code == 401

    @pytest.mark.security
    def test_token_missing_sub_claim(self, client):
        payload = {
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 401

    @pytest.mark.security
    def test_token_with_nonexistent_user_id(self, client):
        payload = {
            "sub": "99999",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 401


class TestAlgorithmConfusion:

    @pytest.mark.security
    def test_none_algorithm_rejected(self, client):
        payload = {
            "sub": "1",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        none_token = pyjwt.encode(payload, key="", algorithm="none")
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {none_token}",
        })
        assert resp.status_code == 401

    @pytest.mark.security
    def test_wrong_secret_rejected(self, client):
        payload = {
            "sub": "1",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        wrong_token = pyjwt.encode(payload, "wrong-secret-key", algorithm="HS256")
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {wrong_token}",
        })
        assert resp.status_code == 401

    @pytest.mark.security
    def test_hs384_algorithm_rejected(self, client):
        payload = {
            "sub": "1",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        wrong_algo_token = pyjwt.encode(payload, JWT_SECRET, algorithm="HS384")
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {wrong_algo_token}",
        })
        assert resp.status_code == 401


class TestTokenTampering:

    @pytest.mark.security
    def test_tampered_payload_rejected(self, client):
        valid_payload = {
            "sub": "1",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = pyjwt.encode(valid_payload, JWT_SECRET, algorithm="HS256")
        tampered = token[:-4] + "AAAA"
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {tampered}",
        })
        assert resp.status_code == 401

    @pytest.mark.security
    def test_basic_auth_scheme_rejected(self, client):
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Basic dGVzdDp0ZXN0",
        })
        assert resp.status_code == 401


class TestIssuerAudienceValidation:
    """JWT must validate issuer (iss) and audience (aud) claims."""

    @pytest.mark.security
    def test_valid_token_with_issuer_and_audience(self, client, create_user):
        """Token with correct issuer and audience should be accepted."""
        user = create_user()
        token = create_token(user.id)
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200

    @pytest.mark.security
    def test_token_with_invalid_issuer_rejected(self, client):
        """Token with wrong issuer should be rejected."""
        payload = {
            "sub": "1",
            "iss": "attacker-site",
            "aud": JWT_AUDIENCE,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 401

    @pytest.mark.security
    def test_token_with_invalid_audience_rejected(self, client):
        """Token with wrong audience should be rejected."""
        payload = {
            "sub": "1",
            "iss": JWT_ISSUER,
            "aud": "attacker-api",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 401

    @pytest.mark.security
    def test_token_missing_issuer_rejected(self, client):
        """Token without issuer should be rejected."""
        payload = {
            "sub": "1",
            "aud": JWT_AUDIENCE,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 401

    @pytest.mark.security
    def test_token_missing_audience_rejected(self, client):
        """Token without audience should be rejected."""
        payload = {
            "sub": "1",
            "iss": JWT_ISSUER,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 401
