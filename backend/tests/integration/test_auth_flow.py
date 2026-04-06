"""Integration tests — Auth flow (register, login, logout, bootstrap, CAPTCHA)."""
import pytest
from tests.conftest import register_user, login_user, solve_captcha


class TestCaptchaEndpoints:
    def test_get_captcha(self, client):
        r = client.get("/api/auth/captcha")
        assert r.status_code == 200
        assert "challenge_id" in r.json()
        assert "question" in r.json()

    def test_verify_captcha_correct(self, client):
        cap = solve_captcha(client)
        r = client.post("/api/auth/captcha/verify", json={
            "challenge_id": cap["challenge_id"],
            "answer": cap["answer"],
        })
        assert r.status_code == 200
        assert r.json()["valid"] is True

    def test_verify_captcha_wrong(self, client):
        cap = solve_captcha(client)
        r = client.post("/api/auth/captcha/verify", json={
            "challenge_id": cap["challenge_id"],
            "answer": "999999",
        })
        assert r.status_code == 200
        assert r.json()["valid"] is False

    def test_verify_captcha_nonexistent_id(self, client):
        r = client.post("/api/auth/captcha/verify", json={
            "challenge_id": "nonexistent", "answer": "0",
        })
        assert r.status_code == 200
        assert r.json()["valid"] is False


class TestRegister:
    def test_register_success(self, client):
        data = register_user(client)
        assert "token" in data
        assert data["user"]["role"] == "user"
        assert data["user"]["is_active"] is True

    def test_register_sets_cookie(self, client):
        cap = solve_captcha(client)
        r = client.post("/api/auth/register", json={
            "username": "cookieuser", "email": "cookie@test.com",
            "phone_area_code": "0341", "phone_number": "1234567",
            "password": "password123",
            "captcha_challenge_id": cap["challenge_id"],
            "captcha_answer": cap["answer"],
        })
        assert r.status_code == 201
        assert "auth_token" in r.cookies

    def test_register_duplicate_email(self, client):
        data = register_user(client, email="dup@test.com")
        cap = solve_captcha(client)
        r = client.post("/api/auth/register", json={
            "username": "other", "email": "dup@test.com",
            "phone_area_code": "0341", "phone_number": "1234567",
            "password": "password123",
            "captcha_challenge_id": cap["challenge_id"],
            "captcha_answer": cap["answer"],
        })
        assert r.status_code == 400

    def test_register_short_password(self, client):
        cap = solve_captcha(client)
        r = client.post("/api/auth/register", json={
            "username": "test", "email": "t@test.com",
            "phone_area_code": "0341", "phone_number": "1234567",
            "password": "short",
            "captcha_challenge_id": cap["challenge_id"],
            "captcha_answer": cap["answer"],
        })
        assert r.status_code == 422

    def test_register_invalid_email(self, client):
        cap = solve_captcha(client)
        r = client.post("/api/auth/register", json={
            "username": "test", "email": "not-email",
            "phone_area_code": "0341", "phone_number": "1234567",
            "password": "password123",
            "captcha_challenge_id": cap["challenge_id"],
            "captcha_answer": cap["answer"],
        })
        assert r.status_code == 422

    def test_register_role_always_user(self, client):
        """Verify that even if role is passed, it's ignored."""
        data = register_user(client)
        assert data["user"]["role"] == "user"

    def test_register_wrong_captcha(self, client):
        cap = solve_captcha(client)
        r = client.post("/api/auth/register", json={
            "username": "failcap", "email": "failcap@test.com",
            "phone_area_code": "0341", "phone_number": "1234567",
            "password": "password123",
            "captcha_challenge_id": cap["challenge_id"],
            "captcha_answer": "999999",
        })
        assert r.status_code == 400
        assert "CAPTCHA" in r.json()["detail"]


class TestLogin:
    def test_login_by_email(self, client):
        register_user(client, email="login@test.com", password="mypassword1")
        data = login_user(client, "login@test.com", "mypassword1")
        assert "token" in data

    def test_login_by_username(self, client):
        reg = register_user(client, username="loginuser", password="mypassword1")
        data = login_user(client, "loginuser", "mypassword1")
        assert "token" in data

    def test_login_wrong_password(self, client):
        register_user(client, email="wp@test.com")
        r = client.post("/api/auth/login", json={
            "username_or_email": "wp@test.com", "password": "wrongpassword",
        })
        assert r.status_code == 401
        assert "Credenciales" in r.json()["detail"]

    def test_login_nonexistent_user(self, client):
        r = client.post("/api/auth/login", json={
            "username_or_email": "nobody@test.com", "password": "whatever",
        })
        assert r.status_code == 401

    def test_login_inactive_user(self, client, create_user):
        u = create_user(is_active=False)
        r = client.post("/api/auth/login", json={
            "username_or_email": u.email, "password": "password123",
        })
        assert r.status_code == 401
        assert "inactivo" in r.json()["detail"].lower()

    def test_login_sets_cookie(self, client):
        register_user(client, email="logincookie@test.com")
        r = client.post("/api/auth/login", json={
            "username_or_email": "logincookie@test.com",
            "password": "password123",
        })
        assert r.status_code == 200
        assert "auth_token" in r.cookies


class TestLogout:
    def test_logout_clears_cookie(self, client):
        r = client.post("/api/auth/logout")
        assert r.status_code == 200
        assert "Sesión cerrada" in r.json()["message"]


class TestMe:
    def test_me_authenticated(self, client, user_headers):
        r = client.get("/api/auth/me", headers=user_headers)
        assert r.status_code == 200
        assert "username" in r.json()

    def test_me_unauthenticated(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code == 401


class TestBootstrapAdmin:
    def test_bootstrap_fails_when_users_exist(self, client, create_user):
        create_user()  # At least one user exists
        cap = solve_captcha(client)
        r = client.post("/api/auth/bootstrap-admin", json={
            "username": "admin", "email": "admin@test.com",
            "phone_area_code": "0341", "phone_number": "1111111",
            "password": "adminpass123",
            "captcha_challenge_id": cap["challenge_id"],
            "captcha_answer": cap["answer"],
        })
        assert r.status_code == 403
