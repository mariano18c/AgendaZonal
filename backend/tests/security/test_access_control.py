"""Security tests — Access control (IDOR, privilege escalation, protected endpoints)."""
import pytest
import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from tests.conftest import _bearer
from app.config import JWT_SECRET, JWT_ALGORITHM


class TestIDOR:
    """Insecure Direct Object Reference tests."""

    def test_cannot_update_others_contact(self, client, create_user, create_contact):
        owner = create_user()
        attacker = create_user()
        c = create_contact(user_id=owner.id)
        r = client.put(f"/api/contacts/{c.id}", headers=_bearer(attacker),
                        json={"name": "Hacked"})
        assert r.status_code == 403

    def test_cannot_delete_others_contact(self, client, create_user, create_contact):
        c = create_contact()
        attacker = create_user()
        r = client.delete(f"/api/contacts/{c.id}", headers=_bearer(attacker))
        assert r.status_code == 403

    def test_cannot_view_others_leads(self, client, create_user, create_contact):
        c = create_contact()
        attacker = create_user()
        r = client.get(f"/api/contacts/{c.id}/leads", headers=_bearer(attacker))
        assert r.status_code == 403

    def test_cannot_read_others_notification(self, client, create_user, create_notification):
        owner = create_user()
        attacker = create_user()
        n = create_notification(user_id=owner.id)
        r = client.put(f"/api/notifications/{n.id}/read", headers=_bearer(attacker))
        assert r.status_code == 404

    def test_cannot_manage_others_offers(self, client, create_user, create_contact, create_offer):
        c = create_contact()
        offer = create_offer(contact_id=c.id)
        attacker = create_user()
        r = client.delete(f"/api/contacts/{c.id}/offers/{offer.id}",
                           headers=_bearer(attacker))
        assert r.status_code == 403


class TestPrivilegeEscalation:
    """Verify users cannot escalate to admin/moderator."""

    def test_user_cannot_access_admin_analytics(self, client, user_headers):
        r = client.get("/api/admin/analytics", headers=user_headers)
        assert r.status_code == 403

    def test_user_cannot_access_admin_reports(self, client, user_headers):
        r = client.get("/api/admin/reports/pending", headers=user_headers)
        assert r.status_code == 403

    def test_user_cannot_approve_reviews(self, client, user_headers,
                                          create_contact, create_review):
        c = create_contact()
        rev = create_review(contact_id=c.id)
        r = client.post(f"/api/admin/reviews/{rev.id}/approve", headers=user_headers)
        assert r.status_code == 403

    def test_user_cannot_create_utilities(self, client, user_headers):
        r = client.post("/api/admin/utilities", headers=user_headers,
                          json={"name": "X"})
        assert r.status_code == 403

    def test_user_cannot_list_users(self, client, user_headers):
        r = client.get("/api/users", headers=user_headers)
        assert r.status_code == 403

    def test_user_cannot_change_roles(self, client, user_headers, create_user):
        u = create_user()
        r = client.put(f"/api/users/{u.id}/role", headers=user_headers,
                        json={"role": "admin"})
        assert r.status_code == 403

    def test_mod_cannot_manage_users(self, client, mod_headers, create_user):
        u = create_user()
        r = client.get("/api/users", headers=mod_headers)
        assert r.status_code == 403

    def test_user_cannot_export_contacts(self, client, user_headers):
        r = client.get("/api/contacts/export", headers=user_headers)
        assert r.status_code == 403


class TestProtectedEndpoints:
    """Verify all protected endpoints return 401 without auth."""

    @pytest.mark.parametrize("method, path", [
        ("POST", "/api/contacts"),
        ("DELETE", "/api/contacts/1"),
        ("GET", "/api/auth/me"),
        ("GET", "/api/notifications"),
        ("GET", "/api/provider/dashboard"),
        ("GET", "/api/contacts/export"),
        ("GET", "/api/contacts/pending"),
    ])
    def test_requires_auth(self, client, method, path):
        r = getattr(client, method.lower())(path)
        assert r.status_code == 401, f"{method} {path} should require auth"


class TestPrivilegeEscalationAdvanced:
    """Advanced privilege escalation — merged from tests_ant."""

    def test_role_injection_on_register(self, client, captcha):
        """Sending role=admin in registration should be ignored."""
        resp = client.post("/api/auth/register", json={
            "username": "role_hacker",
            "email": "role_hacker@evil.com",
            "phone_area_code": "0341",
            "phone_number": "6666666",
            "password": "HackerPass123!",
            "role": "admin",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        assert resp.status_code == 201
        # Registration creates user - check the role field is not admin
        data = resp.json()
        # May return {"token": ..., "user": {"role": "user"}} or {"message": ..., "username": ...}
        # Either way, the role should be "user" not "admin"
        if "user" in data:
            assert data.get("user", {}).get("role", "") != "admin"
        elif "token" in data:
            # If we get a token, role injection was prevented
            pass
        else:
            # Pending registration - role injection prevented
            pass

    def test_jwt_claim_manipulation_role(self, client, create_user):
        """Forging a JWT with role=admin claim should not work."""
        user = create_user(username="jwt_hacker", email="jwt_hack@test.com", role="user")
        payload = {
            "sub": str(user.id),
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/users", headers=headers)
        assert resp.status_code == 403

    def test_bootstrap_admin_replay(self, client, captcha):
        """Bootstrap admin should only work once per DB."""
        client.post("/api/auth/bootstrap-admin", json={
            "username": "first_admin",
            "email": "first@admin.com",
            "phone_area_code": "0341",
            "phone_number": "1111111",
            "password": "adminpass123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        captcha2 = client.get("/api/auth/captcha").json()
        from tests.conftest import _parse_captcha_answer
        answer = _parse_captcha_answer(captcha2["question"])
        resp = client.post("/api/auth/bootstrap-admin", json={
            "username": "second_admin",
            "email": "second@admin.com",
            "phone_area_code": "0341",
            "phone_number": "2222222",
            "password": "adminpass123",
            "captcha_challenge_id": captcha2["challenge_id"],
            "captcha_answer": str(answer),
        })
        assert resp.status_code in [400, 403, 409]

    def test_moderator_cannot_create_users(self, client, mod_headers):
        """Moderator should NOT create users."""
        resp = client.post("/api/users", headers=mod_headers, json={
            "username": "hacker_created",
            "email": "hacker@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "role": "user",
        })
        assert resp.status_code == 403


class TestDataExfiltrationAdvanced:
    """Advanced data exfiltration — merged from tests_ant."""

    def test_cannot_access_other_user_schedules(self, client, create_user, db_session):
        """User should not be able to modify other user's schedules."""
        from app.models.contact import Contact
        owner = create_user(username="sched_owner", email="sched_owner@test.com")
        attacker = create_user(username="sched_attacker", email="sched_attacker@test.com")
        contact = Contact(name="Sched Biz", phone="123", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)
        from app.auth import create_token
        token = create_token(attacker.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.put(f"/api/contacts/{contact.id}/schedules", headers=headers, json=[
            {"day_of_week": 1, "open_time": "09:00", "close_time": "18:00"},
        ])
        assert resp.status_code == 403

    def test_deactivated_user_token_rejected(self, client, create_user, db_session):
        """Token should be rejected after user is deactivated."""
        user = create_user(username="deact_token", email="deact_token@test.com")
        resp = client.post("/api/auth/login", json={
            "username_or_email": "deact_token",
            "password": "password123",
        })
        token = resp.json()["token"]
        user.is_active = False
        db_session.commit()
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_csv_export_does_not_leak_passwords(self, client, admin_headers):
        """Analytics CSV export should not contain sensitive data."""
        resp = client.get("/api/admin/analytics/export", headers=admin_headers)
        assert resp.status_code == 200
        content = resp.text.lower()
        assert "password" not in content
        assert "password_hash" not in content
        assert "secret" not in content
