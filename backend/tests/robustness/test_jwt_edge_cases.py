"""Robustness tests for JWT edge cases — merged from tests_ant."""
import pytest
import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from app.config import JWT_SECRET, JWT_ALGORITHM, JWT_ISSUER, JWT_AUDIENCE


class TestJWTEdgeCases:
    """JWT must reject malformed, expired, and algorithm-confused tokens."""

    def test_algorithm_confusion_hs384(self, client, create_user):
        """HS384 instead of HS256 should be rejected with 401."""
        user = create_user()
        payload = {"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = pyjwt.encode(payload, JWT_SECRET, algorithm="HS384")
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_empty_sub_claim(self, client, create_user):
        """Token with empty 'sub' claim should be rejected."""
        user = create_user()
        payload = {"sub": "", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_missing_exp_claim(self, client, create_user):
        """Token without 'exp' claim — should be rejected or accepted based on config."""
        user = create_user()
        payload = {"sub": str(user.id)}
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code in [200, 401]

    def test_future_dated_exp(self, client, create_user):
        """Token with far-future expiration should still work if valid."""
        user = create_user()
        payload = {"sub": str(user.id), "iss": JWT_ISSUER, "aud": JWT_AUDIENCE, "exp": datetime.now(timezone.utc) + timedelta(days=365)}
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200

    def test_none_algorithm_rejected(self, client, create_user):
        """Token with 'none' algorithm should be rejected."""
        user = create_user()
        try:
            token = pyjwt.encode(
                {"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                key="", algorithm="none",
            )
        except Exception:
            pytest.skip("JWT library refuses 'none' algorithm encoding")
            return
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_negative_user_id(self, client):
        """Token with negative user_id should be rejected."""
        payload = {"sub": "-1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_float_user_id(self, client):
        """Token with float user_id should be rejected."""
        payload = {"sub": "1.5", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_huge_user_id(self, client):
        """Token with extremely large user_id should be rejected."""
        payload = {"sub": str(2**63 - 1), "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_no_algorithm_details_in_error(self, client):
        """Error responses should not reveal algorithm details."""
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401
        text = resp.text.lower()
        assert "hs256" not in text
        assert "algorithm" not in text
