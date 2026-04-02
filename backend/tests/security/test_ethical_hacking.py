"""Ethical hacking tests — attempt to penetrate the system for unauthorized data access."""
import pytest
import jwt
from datetime import datetime, timedelta, timezone
from app.config import JWT_SECRET, JWT_ALGORITHM


class TestPrivilegeEscalation:
    """Attempt to escalate privileges through various vectors."""

    def test_cannot_register_as_admin(self, client, captcha):
        """Registration should always assign role='user', never admin."""
        resp = client.post("/api/auth/register", json={
            "username": "hacker",
            "email": "hacker@evil.com",
            "phone_area_code": "0341",
            "phone_number": "6666666",
            "password": "HackerPass123!",
            "role": "admin",  # Trying to inject admin role
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        assert resp.status_code == 201
        # Even if we send role=admin, the server should ignore it
        assert resp.json()["user"]["role"] == "user"

    def test_regular_user_cannot_access_admin_endpoints(self, client, auth_headers):
        """Regular user should get 403 on ALL admin endpoints."""
        headers = auth_headers(username="regular", email="regular@test.com")

        admin_endpoints = [
            ("GET", "/api/users"),
            ("GET", "/api/admin/reviews/pending"),
            ("GET", "/api/admin/reports/flagged"),
            ("GET", "/api/admin/analytics"),
            ("GET", "/api/admin/analytics/export"),
        ]

        for method, url in admin_endpoints:
            resp = getattr(client, method.lower())(url, headers=headers)
            assert resp.status_code in [401, 403], \
                f"{method} {url} returned {resp.status_code} instead of 401/403"

    def test_regular_user_cannot_access_admin_user_management(self, client, auth_headers):
        """Regular user should get 403 on user management."""
        headers = auth_headers()
        resp = client.get("/api/users", headers=headers)
        assert resp.status_code == 403

    def test_moderator_cannot_access_admin_user_management(self, client, moderator_user):
        """Moderator should NOT access user management endpoints."""
        _, headers = moderator_user
        resp = client.get("/api/users", headers=headers)
        assert resp.status_code == 403

    def test_cannot_create_admin_user_via_api_with_invalid_role(self, client, admin_headers):
        """Even admin-created users should be validated for valid roles."""
        resp = client.post("/api/users", headers=admin_headers, json={
            "username": "newadmin",
            "email": "newadmin@test.com",
            "phone_area_code": "0341",
            "phone_number": "9999999",
            "password": "pass123456",
            "role": "superadmin",  # Invalid role
        })
        assert resp.status_code == 400

    def test_cannot_change_own_role(self, client, admin_headers):
        """Admin should not be able to change their own role."""
        me = client.get("/api/auth/me", headers=admin_headers)
        user_id = me.json()["id"]

        resp = client.put(f"/api/users/{user_id}/role", headers=admin_headers, json={
            "role": "user",
        })
        assert resp.status_code == 400


class TestDataExfiltration:
    """Attempt to access data not meant for us."""

    def test_cannot_view_other_users_notifications(self, client, create_user, database_session):
        from app.models.notification import Notification
        user1 = create_user(username="victim", email="victim@test.com")
        user2 = create_user(username="attacker", email="attacker@test.com")

        database_session.add(Notification(
            user_id=user1.id, type="review", message="Confidential data"
        ))
        database_session.commit()

        resp = client.post("/api/auth/login", json={
            "username_or_email": "attacker",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = client.get("/api/notifications", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_cannot_read_contact_changes_without_permission(self, client, create_user, database_session):
        from app.models.contact import Contact
        user1 = create_user(username="owner", email="owner@test.com")
        user2 = create_user(username="stranger", email="stranger@test.com")

        contact = Contact(name="Private", phone="1234567", user_id=user1.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.post("/api/auth/login", json={
            "username_or_email": "stranger",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = client.get(f"/api/contacts/{contact.id}/changes", headers=headers)
        assert resp.status_code == 403

    def test_deactivated_user_cannot_login(self, client, create_user):
        create_user(is_active=False)
        resp = client.post("/api/auth/login", json={
            "username_or_email": "testuser",
            "password": "password123",
        })
        assert resp.status_code == 401

    def test_deactivated_user_token_rejected(self, client, create_user, database_session):
        """If a user is deactivated AFTER getting a token, the token should be rejected."""
        user = create_user()

        resp = client.post("/api/auth/login", json={
            "username_or_email": "testuser",
            "password": "password123",
        })
        token = resp.json()["token"]

        user.is_active = False
        database_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_non_owner_cannot_view_leads(self, client, create_user, database_session):
        from app.models.contact import Contact
        owner = create_user(username="owner", email="owner@test.com")
        stranger = create_user(username="stranger", email="stranger@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.post("/api/auth/login", json={
            "username_or_email": "stranger",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = client.get(f"/api/contacts/{contact.id}/leads", headers=headers)
        assert resp.status_code == 403


class TestInputManipulation:
    """Attempt to manipulate inputs to bypass validation."""

    def test_negative_contact_id(self, client):
        resp = client.get("/api/contacts/-1")
        assert resp.status_code == 404

    def test_zero_contact_id(self, client):
        resp = client.get("/api/contacts/0")
        assert resp.status_code == 404

    def test_extremely_large_contact_id(self, client):
        resp = client.get("/api/contacts/999999999999")
        assert resp.status_code in [404, 422]

    def test_float_contact_id(self, client):
        resp = client.get("/api/contacts/1.5")
        assert resp.status_code == 422

    def test_string_contact_id(self, client):
        resp = client.get("/api/contacts/abc")
        assert resp.status_code == 422

    def test_empty_json_body_on_create(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={})
        assert resp.status_code == 422

    def test_null_values_in_required_fields(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": None,
            "phone": None,
        })
        assert resp.status_code == 422

    def test_extremely_long_string_in_name(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "A" * 10000,
            "phone": "1234567",
        })
        assert resp.status_code == 422


class TestAuthBypassAttempts:
    """Attempt to bypass authentication."""

    def test_expired_jwt_token(self, client):
        payload = {
            "sub": "1",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_tampered_jwt_token(self, client, create_user):
        user = create_user()
        payload = {
            "sub": str(user.id),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, "wrong_secret", algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_malformed_authorization_header_bearer_only(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer"})
        assert resp.status_code == 401

    def test_malformed_authorization_header_no_scheme(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "just-a-token"})
        assert resp.status_code == 401

    def test_token_with_different_algorithm(self, client, create_user):
        """JWT algorithm confusion attack — should be rejected."""
        user = create_user()
        payload = {
            "sub": str(user.id),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS384")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_empty_token(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401

    def test_cookie_auth_works(self, client, captcha):
        """Verify that cookie-based authentication works after login."""
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

        resp = client.get("/api/auth/me")
        assert resp.status_code == 200


class TestDOSResistance:
    """Attempt denial-of-service attacks."""

    def test_massive_search_query(self, client):
        """Send a very long search query."""
        resp = client.get(f"/api/contacts/search?q={'A' * 10000}")
        assert resp.status_code in [200, 400, 414, 422]

    def test_zero_limit_on_list(self, client):
        resp = client.get("/api/contacts?limit=0")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_negative_skip(self, client):
        resp = client.get("/api/contacts?skip=-1")
        assert resp.status_code in [200, 422]

    def test_huge_limit_capped(self, client):
        resp = client.get("/api/contacts?limit=10000")
        assert resp.status_code == 422

    def test_rapid_login_attempts_no_crash(self, client):
        """Multiple rapid login attempts should not crash the server."""
        for _ in range(20):
            resp = client.post("/api/auth/login", json={
                "username_or_email": "nonexistent",
                "password": "wrong",
            })
            assert resp.status_code == 401
