"""Security tests — JWT auth bypass (expired, wrong secret, forged, etc.)."""
import pytest
from tests.conftest import _bearer


class TestExpiredToken:
    def test_expired_token_rejected(self, client, jwt_helpers):
        token = jwt_helpers.expired()
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_expired_token_on_protected_api(self, client, jwt_helpers):
        token = jwt_helpers.expired()
        r = client.post("/api/contacts", headers={"Authorization": f"Bearer {token}"},
                         json={"name": "X"})
        assert r.status_code == 401


class TestWrongSecret:
    def test_wrong_secret_rejected(self, client, jwt_helpers):
        token = jwt_helpers.wrong_secret()
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


class TestForgedTokens:
    def test_forged_admin_token(self, client, jwt_helpers):
        """Token for non-existent user_id should be rejected."""
        token = jwt_helpers.forged_admin()
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_token_without_sub(self, client, jwt_helpers):
        token = jwt_helpers.no_sub()
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_wrong_algorithm(self, client, jwt_helpers):
        token = jwt_helpers.wrong_algo()
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_non_numeric_sub(self, client, jwt_helpers):
        token = jwt_helpers.non_numeric_sub()
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


class TestMalformedAuth:
    def test_no_bearer_prefix(self, client, create_user):
        user = create_user()
        from app.auth import create_token
        token = create_token(user.id)
        r = client.get("/api/auth/me", headers={"Authorization": token})
        assert r.status_code == 401

    def test_empty_bearer(self, client):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer "})
        assert r.status_code == 401

    def test_garbage_token(self, client):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage.token.here"})
        assert r.status_code == 401

    def test_bearer_with_spaces(self, client):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer   token   "})
        assert r.status_code == 401

    def test_none_authorization(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code == 401


class TestInactiveUserToken:
    def test_inactive_user_rejected(self, client, create_user):
        user = create_user(is_active=False)
        r = client.get("/api/auth/me", headers=_bearer(user))
        assert r.status_code == 401
