"""Robustness tests for JWT edge cases."""
import pytest
import jwt
from datetime import datetime, timedelta, timezone
from app.config import JWT_SECRET, JWT_ALGORITHM


class TestJWTEdgeCases:
    """JWT must reject malformed, expired, and algorithm-confused tokens."""

    @pytest.mark.robustness
    def test_algorithm_confusion_hs384(self, client, create_user):
        """HS384 instead of HS256 should be rejected with 401."""
        user = create_user()
        payload = {
            "sub": str(user.id),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS384")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.robustness
    def test_empty_sub_claim(self, client, create_user):
        """Token with empty 'sub' claim should be rejected."""
        user = create_user()
        payload = {
            "sub": "",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.robustness
    def test_missing_exp_claim(self, client, create_user):
        """Token without 'exp' claim — should be rejected or accepted based on config."""
        user = create_user()
        payload = {
            "sub": str(user.id),
            # No 'exp' claim
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        # Either 401 (rejected) or 200 (accepted — no exp validation configured)
        # Both are acceptable; the key is no crash
        assert resp.status_code in [200, 401]

    @pytest.mark.robustness
    def test_future_dated_exp(self, client, create_user):
        """Token with far-future expiration should still work if valid."""
        user = create_user()
        payload = {
            "sub": str(user.id),
            "exp": datetime.now(timezone.utc) + timedelta(days=365),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        # Should work — far future is still valid
        assert resp.status_code == 200

    @pytest.mark.robustness
    def test_none_algorithm_rejected(self, client, create_user):
        """Token with 'none' algorithm should be rejected."""
        user = create_user()
        payload = {
            "sub": str(user.id),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        try:
            token = jwt.encode(payload, key="", algorithm="none")
        except Exception:
            # Some JWT libraries refuse to encode with 'none' — that's fine
            pytest.skip("JWT library refuses 'none' algorithm encoding")
            return

        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.robustness
    def test_no_algorithm_details_in_error(self, client):
        """Error responses should not reveal algorithm details."""
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer invalid.token.here",
        })
        assert resp.status_code == 401
        text = resp.text.lower()
        assert "hs256" not in text
        assert "algorithm" not in text
