"""Security tests — Access control (IDOR, privilege escalation, protected endpoints)."""
import pytest
from tests.conftest import _bearer


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
