"""Integration tests — Users admin CRUD, role, deactivate, password reset."""
import pytest
from datetime import datetime, timezone
from tests.conftest import _bearer


class TestListUsers:
    def test_list_users_as_admin(self, client, admin_headers, create_user):
        create_user()
        r = client.get("/api/users", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_list_users_filter_active(self, client, admin_headers, create_user):
        create_user(is_active=True)
        r = client.get("/api/users", headers=admin_headers,
                        params={"filter": "active"})
        assert r.status_code == 200
        assert all(u["is_active"] for u in r.json()["users"])

    def test_list_users_filter_inactive(self, client, admin_headers, create_user):
        create_user(is_active=False)
        r = client.get("/api/users", headers=admin_headers,
                        params={"filter": "inactive"})
        assert r.status_code == 200

    def test_list_users_filter_pending(self, client, admin_headers, db_session, create_user):
        """filter=pending returns only is_active=False AND deactivated_at IS NULL."""
        # Create a pending user (is_active=False, deactivated_at=None)
        pending = create_user(is_active=False)
        # Create a deactivated user (is_active=False, deactivated_at set)
        deactivated = create_user(is_active=False)
        deactivated.deactivated_at = datetime.now(timezone.utc)
        db_session.commit()
        db_session.refresh(deactivated)

        r = client.get("/api/users", headers=admin_headers,
                        params={"filter": "pending"})
        assert r.status_code == 200
        users = r.json()["users"]
        assert len(users) >= 1
        assert all(u["status"] == "pending" for u in users)

    def test_list_users_filter_role(self, client, admin_headers, create_user):
        create_user(role="moderator")
        r = client.get("/api/users", headers=admin_headers,
                        params={"role": "moderator"})
        assert r.status_code == 200
        assert all(u["role"] == "moderator" for u in r.json()["users"])

    def test_list_users_search_username(self, client, admin_headers, create_user):
        create_user(username="findable_user")
        r = client.get("/api/users", headers=admin_headers,
                        params={"username": "findable"})
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_list_users_pagination(self, client, admin_headers, create_user):
        for _ in range(3):
            create_user()
        r = client.get("/api/users", headers=admin_headers,
                        params={"skip": 0, "limit": 2})
        assert r.status_code == 200
        assert len(r.json()["users"]) <= 2

    def test_list_users_forbidden_for_user(self, client, user_headers):
        r = client.get("/api/users", headers=user_headers)
        assert r.status_code == 403

    def test_list_active_users_public(self, client, create_user):
        create_user()
        r = client.get("/api/users/active")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        if r.json():
            assert "id" in r.json()[0]
            assert "username" in r.json()[0]

    def test_list_users_includes_status_field(self, client, admin_headers, create_user):
        """All users in list response include derived status field."""
        u = create_user()
        r = client.get("/api/users", headers=admin_headers)
        assert r.status_code == 200
        users = r.json()["users"]
        assert all("status" in u for u in users)
        # Find our user
        our_user = next((x for x in users if x["id"] == u.id), None)
        assert our_user is not None
        assert our_user["status"] == "active"


class TestGetUser:
    def test_get_user_by_admin(self, client, admin_headers, create_user):
        u = create_user()
        r = client.get(f"/api/users/{u.id}", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["username"] == u.username

    def test_get_nonexistent(self, client, admin_headers):
        r = client.get("/api/users/99999", headers=admin_headers)
        assert r.status_code == 404


class TestCreateUser:
    def test_admin_creates_user(self, client, admin_headers):
        r = client.post("/api/users", headers=admin_headers, json={
            "username": "newuser", "email": "new@test.com",
            "phone_area_code": "011", "phone_number": "1234567",
            "password": "password123", "role": "user",
        })
        assert r.status_code == 201
        assert r.json()["username"] == "newuser"

    def test_admin_creates_moderator(self, client, admin_headers):
        r = client.post("/api/users", headers=admin_headers, json={
            "username": "newmod", "email": "newmod@test.com",
            "phone_area_code": "011", "phone_number": "1234567",
            "password": "password123", "role": "moderator",
        })
        assert r.status_code == 201
        assert r.json()["role"] == "moderator"

    def test_duplicate_email(self, client, admin_headers, create_user):
        u = create_user()
        r = client.post("/api/users", headers=admin_headers, json={
            "username": "other", "email": u.email,
            "phone_area_code": "011", "phone_number": "1234567",
            "password": "password123", "role": "user",
        })
        assert r.status_code == 400

    def test_duplicate_username(self, client, admin_headers, create_user):
        u = create_user()
        r = client.post("/api/users", headers=admin_headers, json={
            "username": u.username, "email": "unique@test.com",
            "phone_area_code": "011", "phone_number": "1234567",
            "password": "password123", "role": "user",
        })
        assert r.status_code == 400

    def test_invalid_role(self, client, admin_headers):
        r = client.post("/api/users", headers=admin_headers, json={
            "username": "badrole", "email": "bad@test.com",
            "phone_area_code": "011", "phone_number": "1234567",
            "password": "password123", "role": "superadmin",
        })
        assert r.status_code == 400


class TestUpdateUser:
    def test_update_email(self, client, admin_headers, create_user):
        u = create_user()
        r = client.put(f"/api/users/{u.id}", headers=admin_headers,
                        json={"email": "updated@test.com"})
        assert r.status_code == 200
        assert r.json()["email"] == "updated@test.com"

    def test_update_password(self, client, admin_headers, create_user):
        u = create_user()
        r = client.put(f"/api/users/{u.id}", headers=admin_headers,
                        json={"password": "newpassword123"})
        assert r.status_code == 200

    def test_cannot_change_admin_role(self, client, admin_headers, admin_user):
        r = client.put(f"/api/users/{admin_user.id}", headers=admin_headers,
                        json={"role": "user"})
        assert r.status_code == 400


class TestUpdateRole:
    def test_change_role(self, client, admin_headers, create_user):
        u = create_user()
        r = client.put(f"/api/users/{u.id}/role", headers=admin_headers,
                        json={"role": "moderator"})
        assert r.status_code == 200
        assert r.json()["role"] == "moderator"

    def test_cannot_change_own_role(self, client, admin_headers, admin_user):
        r = client.put(f"/api/users/{admin_user.id}/role", headers=admin_headers,
                        json={"role": "user"})
        assert r.status_code == 400

    def test_invalid_role(self, client, admin_headers, create_user):
        u = create_user()
        r = client.put(f"/api/users/{u.id}/role", headers=admin_headers,
                        json={"role": "god"})
        assert r.status_code == 400


class TestDeactivateActivate:
    def test_deactivate_user(self, client, admin_headers, create_user):
        u = create_user()
        r = client.delete(f"/api/users/{u.id}", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["is_active"] is False
        assert r.json()["deactivated_at"] is not None

    def test_cannot_deactivate_self(self, client, admin_headers, admin_user):
        r = client.delete(f"/api/users/{admin_user.id}", headers=admin_headers)
        assert r.status_code == 400

    def test_activate_user(self, client, admin_headers, create_user):
        u = create_user(is_active=False)
        r = client.post(f"/api/users/{u.id}/activate", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["is_active"] is True


class TestResetPassword:
    def test_reset_password(self, client, admin_headers, create_user):
        u = create_user()
        r = client.post(f"/api/users/{u.id}/reset-password",
                          headers=admin_headers,
                          json={"new_password": "newpassword123"})
        assert r.status_code == 200

    def test_reset_password_too_short(self, client, admin_headers, create_user):
        u = create_user()
        r = client.post(f"/api/users/{u.id}/reset-password",
                          headers=admin_headers,
                          json={"new_password": "short"})
        assert r.status_code == 422

    def test_reset_password_nonexistent(self, client, admin_headers):
        r = client.post("/api/users/99999/reset-password",
                          headers=admin_headers,
                          json={"new_password": "newpassword123"})
        assert r.status_code == 404


class TestApproveReject:
    def test_approve_pending_user(self, client, admin_headers, create_user):
        u = create_user(is_active=False)  # pending: deactivated_at is None
        r = client.post(f"/api/users/{u.id}/approve", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["is_active"] is True
        assert r.json()["deactivated_at"] is None

    def test_approve_already_active_user(self, client, admin_headers, create_user):
        u = create_user(is_active=True)
        r = client.post(f"/api/users/{u.id}/approve", headers=admin_headers)
        assert r.status_code == 400
        assert "ya está activo" in r.json()["detail"].lower()

    def test_reject_pending_user(self, client, admin_headers, create_user, admin_user):
        u = create_user(is_active=False)  # pending
        r = client.post(f"/api/users/{u.id}/reject", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["is_active"] is False
        assert r.json()["deactivated_at"] is not None
        assert r.json()["deactivated_by"] == admin_user.id

    def test_reject_already_deactivated_user(self, client, admin_headers, db_session, create_user):
        u = create_user(is_active=False)
        u.deactivated_at = datetime.now(timezone.utc)
        db_session.commit()
        db_session.refresh(u)
        r = client.post(f"/api/users/{u.id}/reject", headers=admin_headers)
        assert r.status_code == 400
        assert "ya fue rechazado" in r.json()["detail"].lower()

    def test_approve_non_admin_forbidden(self, client, user_headers, create_user):
        u = create_user(is_active=False)
        r = client.post(f"/api/users/{u.id}/approve", headers=user_headers)
        assert r.status_code == 403

    def test_reject_non_admin_forbidden(self, client, user_headers, create_user):
        u = create_user(is_active=False)
        r = client.post(f"/api/users/{u.id}/reject", headers=user_headers)
        assert r.status_code == 403

    def test_approve_nonexistent(self, client, admin_headers):
        r = client.post("/api/users/99999/approve", headers=admin_headers)
        assert r.status_code == 404

    def test_reject_nonexistent(self, client, admin_headers):
        r = client.post("/api/users/99999/reject", headers=admin_headers)
        assert r.status_code == 404
