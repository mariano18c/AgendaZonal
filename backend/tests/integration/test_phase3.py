"""Integration tests for Phase 3: Offers, Leads, Dashboard."""
from datetime import datetime, timedelta, timezone
import pytest


class TestOffers:
    """Test offers CRUD."""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_headers, contact_factory):
        self.owner_headers = auth_headers(username="off_owner", email="offowner@test.com")
        self.other_headers = auth_headers(username="off_other", email="offother@test.com")
        self.contact_id = contact_factory(
            self.owner_headers, name="Offer Contact", phone="3411111111",
            category_id=1,
        )
        self.future_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    def test_create_offer(self, client):
        resp = client.post(f"/api/contacts/{self.contact_id}/offers",
            headers=self.owner_headers,
            json={"title": "20% descuento", "discount_pct": 20, "expires_at": self.future_date},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "20% descuento"
        assert data["discount_pct"] == 20
        assert data["is_active"] is True

    def test_create_offer_past_date(self, client):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        resp = client.post(f"/api/contacts/{self.contact_id}/offers",
            headers=self.owner_headers,
            json={"title": "Expired", "expires_at": past},
        )
        assert resp.status_code == 400

    def test_non_owner_cannot_create(self, client):
        resp = client.post(f"/api/contacts/{self.contact_id}/offers",
            headers=self.other_headers,
            json={"title": "Hack", "expires_at": self.future_date},
        )
        assert resp.status_code == 403

    def test_list_offers(self, client):
        client.post(f"/api/contacts/{self.contact_id}/offers",
            headers=self.owner_headers,
            json={"title": "Oferta 1", "expires_at": self.future_date},
        )
        client.post(f"/api/contacts/{self.contact_id}/offers",
            headers=self.owner_headers,
            json={"title": "Oferta 2", "discount_pct": 30, "expires_at": self.future_date},
        )
        resp = client.get(f"/api/contacts/{self.contact_id}/offers")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_expired_offers_not_listed(self, client):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        # Insert directly to DB to bypass validation
        from app.database import SessionLocal
        from app.models.offer import Offer
        db = SessionLocal()
        try:
            offer = Offer(
                contact_id=self.contact_id, title="Expired",
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),
                is_active=True,
            )
            db.add(offer)
            db.commit()
        finally:
            db.close()

        resp = client.get(f"/api/contacts/{self.contact_id}/offers")
        assert len(resp.json()) == 0

    def test_update_offer(self, client):
        create_resp = client.post(f"/api/contacts/{self.contact_id}/offers",
            headers=self.owner_headers,
            json={"title": "Old", "expires_at": self.future_date},
        )
        offer_id = create_resp.json()["id"]

        new_future = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        resp = client.put(f"/api/contacts/{self.contact_id}/offers/{offer_id}",
            headers=self.owner_headers,
            json={"title": "Updated", "discount_pct": 50, "expires_at": new_future},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"
        assert resp.json()["discount_pct"] == 50

    def test_delete_offer(self, client):
        create_resp = client.post(f"/api/contacts/{self.contact_id}/offers",
            headers=self.owner_headers,
            json={"title": "ToDelete", "expires_at": self.future_date},
        )
        offer_id = create_resp.json()["id"]

        resp = client.delete(f"/api/contacts/{self.contact_id}/offers/{offer_id}",
            headers=self.owner_headers,
        )
        assert resp.status_code == 204

        # Verify deleted
        offers = client.get(f"/api/contacts/{self.contact_id}/offers").json()
        assert len(offers) == 0


class TestLeads:
    """Test WhatsApp lead tracking."""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_headers, contact_factory):
        self.owner_headers = auth_headers(username="lead_owner", email="leadowner@test.com")
        self.user_headers = auth_headers(username="lead_user", email="leaduser@test.com")
        self.contact_id = contact_factory(
            self.owner_headers, name="Lead Contact", phone="3411111111",
            category_id=1,
        )

    def test_register_lead(self, client):
        resp = client.post(f"/api/contacts/{self.contact_id}/leads",
            headers=self.user_headers,
            json={"source": "whatsapp"},
        )
        assert resp.status_code == 201

    def test_register_lead_anonymous(self, client):
        resp = client.post(f"/api/contacts/{self.contact_id}/leads",
            json={"source": "whatsapp"},
        )
        assert resp.status_code == 201

    def test_owner_sees_leads(self, client):
        # Register 3 leads
        for _ in range(3):
            client.post(f"/api/contacts/{self.contact_id}/leads",
                headers=self.user_headers,
                json={"source": "whatsapp"},
            )

        resp = client.get(f"/api/contacts/{self.contact_id}/leads",
            headers=self.owner_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert data["by_source"]["whatsapp"] == 3

    def test_non_owner_cannot_see_leads(self, client):
        resp = client.get(f"/api/contacts/{self.contact_id}/leads",
            headers=self.user_headers,
        )
        assert resp.status_code == 403


class TestDashboard:
    """Test provider dashboard."""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_headers, contact_factory):
        self.owner_headers = auth_headers(username="dash_owner", email="dashowner@test.com")
        self.contact_id = contact_factory(
            self.owner_headers, name="Dash Contact", phone="3411111111",
            category_id=1,
        )

    def test_dashboard_returns_data(self, client):
        resp = client.get("/api/provider/dashboard", headers=self.owner_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_contacts"] >= 1
        assert "leads_this_month" in data
        assert "leads_last_month" in data
        assert "active_offers" in data
        assert "leads_by_week" in data
        assert "recent_reviews" in data
        assert len(data["contacts"]) >= 1

    def test_dashboard_without_auth(self, client):
        # Clear cookies to ensure no auth is sent
        client.cookies.clear()
        resp = client.get("/api/provider/dashboard")
        assert resp.status_code == 401

    def test_dashboard_without_contacts(self, client, auth_headers):
        """User with no contacts gets 404."""
        no_contacts_headers = auth_headers(username="dash_nobody", email="dashnobody@test.com")
        resp = client.get("/api/provider/dashboard", headers=no_contacts_headers)
        assert resp.status_code == 404
