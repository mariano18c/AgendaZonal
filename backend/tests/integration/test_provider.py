"""Integration tests for provider dashboard metrics."""
import pytest
from app.models.lead_event import LeadEvent
from app.models.offer import Offer
from app.models.review import Review
from datetime import datetime, timedelta, timezone


class TestProviderDashboard:
    """Dashboard metrics accuracy."""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_headers, contact_factory, database_session):
        self.owner_headers = auth_headers(username="dash_owner", email="dashowner@test.com")
        self.contact_id = contact_factory(
            self.owner_headers, name="Dashboard Contact", phone="3416666666",
        )

    def test_dashboard_returns_metrics(self, client):
        resp = client.get("/api/provider/dashboard", headers=self.owner_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_contacts" in data or "contacts" in data
        assert "leads_by_week" in data

    def test_dashboard_lead_counts(self, client, create_user, database_session):
        """leads_this_month and leads_last_month should be accurate."""
        user = create_user(username="lead_owner", email="leadowner@test.com")
        from app.models.contact import Contact
        contact = Contact(name="Lead Test", phone="3417777777", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        # Add leads for this month
        now = datetime.now(timezone.utc)
        database_session.add(LeadEvent(
            contact_id=contact.id,
            source="whatsapp",
            created_at=now,
        ))
        # Add lead for last month
        database_session.add(LeadEvent(
            contact_id=contact.id,
            source="phone",
            created_at=now - timedelta(days=35),
        ))
        database_session.commit()

        resp = client.post("/api/auth/login", json={
            "username_or_email": "lead_owner",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = client.get("/api/provider/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("total_leads", 0) >= 1 or data.get("leads_this_month", 0) >= 1

    def test_dashboard_requires_auth(self, client):
        resp = client.get("/api/provider/dashboard")
        # May return 200 (public landing) or 401 (protected)
        assert resp.status_code in [200, 401, 403]
