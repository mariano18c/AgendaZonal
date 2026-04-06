"""Integration tests — Provider dashboard."""
import pytest
from tests.conftest import _bearer


class TestProviderDashboard:
    def test_dashboard_with_contacts(self, client, create_user, create_contact, create_offer, create_review):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        create_offer(contact_id=c.id)
        create_review(contact_id=c.id, is_approved=True, rating=4)
        r = client.get("/api/provider/dashboard", headers=_bearer(owner))
        assert r.status_code == 200
        data = r.json()
        assert "contacts" in data
        assert len(data["contacts"]) >= 1

    def test_dashboard_no_contacts(self, client, create_user):
        user = create_user()
        r = client.get("/api/provider/dashboard", headers=_bearer(user))
        assert r.status_code in (200, 404)

    def test_dashboard_unauthenticated(self, client):
        r = client.get("/api/provider/dashboard")
        assert r.status_code == 401
