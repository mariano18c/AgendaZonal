"""Integration tests — Auth flow (register, login, logout, me, bootstrap)."""
import pytest
from app.models.user import User


class TestAuthRegistration:
    """Test user registration flow."""

    def test_register_new_user_success(self, client, captcha):
        """Valid registration should return 201 with token and user data."""
        resp = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "newuser@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "securepass123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "token" in data
        assert data["user"]["username"] == "newuser"
        assert data["user"]["role"] == "user"
        assert data["user"]["email"] == "newuser@test.com"

    def test_register_sets_auth_cookie(self, client, captcha):
        """Registration should set HttpOnly auth_token cookie."""
        resp = client.post("/api/auth/register", json={
            "username": "cookieuser",
            "email": "cookie@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        assert resp.status_code == 201
        assert "auth_token" in resp.cookies

    def test_register_duplicate_username(self, client, captcha):
        """Duplicate username should return 400."""
        # First registration
        client.post("/api/auth/register", json={
            "username": "duplicate",
            "email": "first@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        # Second with same username
        captcha2 = client.get("/api/auth/captcha").json()
        from tests.conftest import _parse_captcha_answer
        answer = _parse_captcha_answer(captcha2["question"])
        resp = client.post("/api/auth/register", json={
            "username": "duplicate",
            "email": "second@test.com",
            "phone_area_code": "0341",
            "phone_number": "7654321",
            "password": "password123",
            "captcha_challenge_id": captcha2["challenge_id"],
            "captcha_answer": str(answer),
        })
        assert resp.status_code == 400

    def test_register_duplicate_email(self, client, captcha):
        """Duplicate email should return 400."""
        client.post("/api/auth/register", json={
            "username": "user1",
            "email": "dupemail@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        captcha2 = client.get("/api/auth/captcha").json()
        from tests.conftest import _parse_captcha_answer
        answer = _parse_captcha_answer(captcha2["question"])
        resp = client.post("/api/auth/register", json={
            "username": "user2",
            "email": "dupemail@test.com",
            "phone_area_code": "0341",
            "phone_number": "7654321",
            "password": "password123",
            "captcha_challenge_id": captcha2["challenge_id"],
            "captcha_answer": str(answer),
        })
        assert resp.status_code == 400

    def test_register_invalid_captcha(self, client):
        """Wrong CAPTCHA answer should return 400."""
        captcha = client.get("/api/auth/captcha").json()
        resp = client.post("/api/auth/register", json={
            "username": "badcaptcha",
            "email": "bad@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": "9999",  # Wrong answer
        })
        assert resp.status_code == 400

    def test_register_missing_fields(self, client, captcha):
        """Missing required fields should return 422."""
        resp = client.post("/api/auth/register", json={
            "username": "incomplete",
        })
        assert resp.status_code == 422

    def test_register_always_assigns_user_role(self, client, captcha):
        """Even if role=admin is sent, server should assign 'user'."""
        resp = client.post("/api/auth/register", json={
            "username": "roleinject",
            "email": "roleinject@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "role": "admin",  # Ignored by server
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        assert resp.status_code == 201
        assert resp.json()["user"]["role"] == "user"


class TestAuthLogin:
    """Test user login flow."""

    def test_login_with_username(self, client, create_user):
        """Login with username should return token."""
        create_user(username="loginuser", email="login@test.com", password="pass123")
        resp = client.post("/api/auth/login", json={
            "username_or_email": "loginuser",
            "password": "pass123",
        })
        assert resp.status_code == 200
        assert "token" in resp.json()

    def test_login_with_email(self, client, create_user):
        """Login with email should return token."""
        create_user(username="emaillogin", email="emaillogin@test.com", password="pass123")
        resp = client.post("/api/auth/login", json={
            "username_or_email": "emaillogin@test.com",
            "password": "pass123",
        })
        assert resp.status_code == 200
        assert "token" in resp.json()

    def test_login_wrong_password(self, client, create_user):
        """Wrong password should return 401."""
        create_user(username="wrongpass", email="wrong@test.com", password="correct")
        resp = client.post("/api/auth/login", json={
            "username_or_email": "wrongpass",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Non-existent user should return 401."""
        resp = client.post("/api/auth/login", json={
            "username_or_email": "nobody",
            "password": "anything",
        })
        assert resp.status_code == 401

    def test_login_deactivated_user(self, client, create_user):
        """Deactivated user should return 401."""
        create_user(username="deactivated", email="deact@test.com", is_active=False)
        resp = client.post("/api/auth/login", json={
            "username_or_email": "deactivated",
            "password": "password123",
        })
        assert resp.status_code == 401

    def test_login_sets_cookie(self, client, create_user):
        """Login should set auth_token cookie."""
        create_user(username="cookieuser2", email="cookie2@test.com")
        resp = client.post("/api/auth/login", json={
            "username_or_email": "cookieuser2",
            "password": "password123",
        })
        assert resp.status_code == 200
        assert "auth_token" in resp.cookies


class TestAuthMe:
    """Test /api/auth/me endpoint."""

    def test_get_current_user_with_header(self, client, auth_headers):
        """GET /api/auth/me with Bearer token should return user info."""
        headers = auth_headers(username="meuser", email="me@test.com")
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "meuser"
        assert resp.json()["email"] == "me@test.com"

    def test_get_current_user_with_cookie(self, client, captcha):
        """GET /api/auth/me with auth cookie should return user info."""
        client.post("/api/auth/register", json={
            "username": "cookieme",
            "email": "cookieme@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        assert resp.json()["username"] == "cookieme"

    def test_get_current_user_no_auth(self, client):
        """GET /api/auth/me without auth should return 401."""
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """GET /api/auth/me with invalid token should return 401."""
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401


class TestAuthLogout:
    """Test logout flow."""

    def test_logout_clears_cookie(self, client, captcha):
        """Logout should clear auth_token cookie."""
        client.post("/api/auth/register", json={
            "username": "logoutuser",
            "email": "logout@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200
        # Cookie should be cleared — check Set-Cookie header for max-age=0 or empty value
        set_cookie = resp.headers.get("set-cookie", "")
        assert "auth_token" in set_cookie.lower() or "max-age=0" in set_cookie.lower()

    def test_logout_without_auth(self, client):
        """Logout without auth should still succeed."""
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200


class TestBootstrapAdmin:
    """Test admin bootstrap endpoint."""

    def test_bootstrap_admin_creates_admin(self, client, captcha, db_session):
        """Bootstrap should create an admin user when no admin exists in DB."""
        from app.models.user import User
        # Clean any users from previous tests (SAVEPOINT rollback may not work
        # with StaticPool + commit-in-route pattern)
        db_session.query(User).delete()
        db_session.commit()

        resp = client.post("/api/auth/bootstrap-admin", json={
            "username": "firstadmin",
            "email": "firstadmin@test.com",
            "phone_area_code": "0341",
            "phone_number": "1111111",
            "password": "adminpass123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        assert resp.status_code == 201
        assert resp.json()["user"]["role"] == "admin"

    def test_bootstrap_admin_only_works_once(self, client, captcha):
        """Second bootstrap attempt should fail."""
        # First bootstrap
        client.post("/api/auth/bootstrap-admin", json={
            "username": "admin1",
            "email": "admin1@test.com",
            "phone_area_code": "0341",
            "phone_number": "1111111",
            "password": "adminpass123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        # Second bootstrap
        captcha2 = client.get("/api/auth/captcha").json()
        from tests.conftest import _parse_captcha_answer
        answer = _parse_captcha_answer(captcha2["question"])
        resp = client.post("/api/auth/bootstrap-admin", json={
            "username": "admin2",
            "email": "admin2@test.com",
            "phone_area_code": "0341",
            "phone_number": "2222222",
            "password": "adminpass123",
            "captcha_challenge_id": captcha2["challenge_id"],
            "captcha_answer": str(answer),
        })
        assert resp.status_code in [400, 403, 409]


class TestCaptchaEndpoint:
    """Test CAPTCHA endpoints."""

    def test_get_captcha_returns_challenge(self, client):
        """GET /api/auth/captcha should return challenge_id and question."""
        resp = client.get("/api/auth/captcha")
        assert resp.status_code == 200
        data = resp.json()
        assert "challenge_id" in data
        assert "question" in data

    def test_verify_captcha_correct(self, client):
        """POST /api/auth/captcha/verify with correct answer."""
        captcha_resp = client.get("/api/auth/captcha")
        captcha_data = captcha_resp.json()
        from tests.conftest import _parse_captcha_answer
        answer = _parse_captcha_answer(captcha_data["question"])
        resp = client.post("/api/auth/captcha/verify", json={
            "challenge_id": captcha_data["challenge_id"],
            "answer": str(answer),
        })
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_verify_captcha_wrong(self, client):
        """POST /api/auth/captcha/verify with wrong answer."""
        captcha_resp = client.get("/api/auth/captcha")
        captcha_data = captcha_resp.json()
        resp = client.post("/api/auth/captcha/verify", json={
            "challenge_id": captcha_data["challenge_id"],
            "answer": "9999",
        })
        assert resp.status_code == 200
        assert resp.json()["valid"] is False
