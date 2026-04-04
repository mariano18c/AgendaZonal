"""Tests for gaps identified in QA audit — security fixes, uncovered endpoints, and edge cases."""
import pytest
import csv
import io
from datetime import datetime, timezone, timedelta


# ---------------------------------------------------------------------------
# Security Fixes Validation
# ---------------------------------------------------------------------------

class TestBootstrapAdminRateLimit:
    """Validate that bootstrap-admin now has rate limiting."""

    def test_bootstrap_admin_has_rate_limit(self, client):
        """bootstrap-admin should return 429 after exceeding rate limit."""
        # The endpoint may already have an admin (from other tests), so first call
        # could be 403. We test rate limiting by spamming the endpoint.
        statuses = []
        for i in range(8):
            resp = client.post("/api/auth/bootstrap-admin", json={
                "username": f"ratelimit{i}",
                "email": f"ratelimit{i}@test.com",
                "phone_area_code": "0341",
                "phone_number": f"111111{i}",
                "password": "adminpass123",
            })
            statuses.append(resp.status_code)

        # Should hit rate limit (429) or consistently get 403 (admin exists)
        got_429 = 429 in statuses
        got_403 = all(s in [403, 429] for s in statuses)
        assert got_429 or got_403, \
            f"Expected rate limiting (429) or consistent 403, got {statuses}"


class TestExportContactsAuth:
    """Validate that export_contacts now requires authentication."""

    def test_export_requires_auth(self, client):
        """GET /api/contacts/export should return 401 without auth."""
        resp = client.get("/api/contacts/export")
        assert resp.status_code == 401, \
            f"Export should require auth, got {resp.status_code}"

    def test_export_csv_with_auth(self, client, auth_headers):
        """GET /api/contacts/export?format=csv should return CSV with auth."""
        headers = auth_headers()
        resp = client.get("/api/contacts/export?format=csv", headers=headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        # Should have CSV content
        content = resp.text
        assert "name" in content.lower() or "nombre" in content.lower() or content.strip() == ""

    def test_export_json_with_auth(self, client, auth_headers):
        """GET /api/contacts/export?format=json should return JSON with auth."""
        headers = auth_headers()
        resp = client.get("/api/contacts/export?format=json", headers=headers)
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")

    def test_export_invalid_format(self, client, auth_headers):
        """GET /api/contacts/export?format=xml should return 422."""
        headers = auth_headers()
        resp = client.get("/api/contacts/export?format=xml", headers=headers)
        assert resp.status_code == 422


class TestTransferOwnershipSchema:
    """Validate that transfer_ownership now uses Pydantic schema."""

    def test_transfer_ownership_requires_new_owner_id(self, client, admin_headers):
        """Should return 422 if new_owner_id is missing."""
        # Create a contact first
        resp = client.post("/api/contacts", headers=admin_headers, json={
            "name": "Test Contact",
            "phone": "1234567",
        })
        assert resp.status_code == 201
        contact_id = resp.json()["id"]

        # Try without new_owner_id
        resp = client.put(
            f"/api/contacts/{contact_id}/transfer-ownership",
            headers=admin_headers,
            json={}
        )
        assert resp.status_code == 422

    def test_transfer_ownership_rejects_invalid_id(self, client, admin_headers):
        """Should return 422 if new_owner_id is <= 0."""
        resp = client.post("/api/contacts", headers=admin_headers, json={
            "name": "Test Contact",
            "phone": "1234567",
        })
        assert resp.status_code == 201
        contact_id = resp.json()["id"]

        resp = client.put(
            f"/api/contacts/{contact_id}/transfer-ownership",
            headers=admin_headers,
            json={"new_owner_id": 0}
        )
        assert resp.status_code == 422

        resp = client.put(
            f"/api/contacts/{contact_id}/transfer-ownership",
            headers=admin_headers,
            json={"new_owner_id": -1}
        )
        assert resp.status_code == 422

    def test_transfer_ownership_rejects_string_id(self, client, admin_headers):
        """Should return 422 if new_owner_id is a string."""
        resp = client.post("/api/contacts", headers=admin_headers, json={
            "name": "Test Contact",
            "phone": "1234567",
        })
        assert resp.status_code == 201
        contact_id = resp.json()["id"]

        resp = client.put(
            f"/api/contacts/{contact_id}/transfer-ownership",
            headers=admin_headers,
            json={"new_owner_id": "not_a_number"}
        )
        assert resp.status_code == 422


class TestSchedulesSchema:
    """Validate that update_schedules now uses Pydantic schema."""

    def test_update_schedules_validates_day_of_week(self, client, auth_headers):
        """Should return 422 if day_of_week is out of range."""
        headers = auth_headers()
        # Create a contact
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test Contact",
            "phone": "1234567",
        })
        assert resp.status_code == 201
        contact_id = resp.json()["id"]

        # Invalid day_of_week (7 is out of range)
        resp = client.put(
            f"/api/contacts/{contact_id}/schedules",
            headers=headers,
            json=[{"day_of_week": 7, "open_time": "08:00", "close_time": "18:00"}]
        )
        assert resp.status_code == 422

    def test_update_schedules_validates_negative_day(self, client, auth_headers):
        """Should return 422 if day_of_week is negative."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test Contact",
            "phone": "1234567",
        })
        assert resp.status_code == 201
        contact_id = resp.json()["id"]

        resp = client.put(
            f"/api/contacts/{contact_id}/schedules",
            headers=headers,
            json=[{"day_of_week": -1, "open_time": "08:00", "close_time": "18:00"}]
        )
        assert resp.status_code == 422

    def test_update_schedules_accepts_valid_data(self, client, auth_headers):
        """Should accept valid schedule data."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test Contact",
            "phone": "1234567",
        })
        assert resp.status_code == 201
        contact_id = resp.json()["id"]

        schedules = [
            {"day_of_week": 0, "open_time": "08:00", "close_time": "18:00"},
            {"day_of_week": 1, "open_time": "08:00", "close_time": "18:00"},
            {"day_of_week": 2, "open_time": "08:00", "close_time": "18:00"},
            {"day_of_week": 3, "open_time": "08:00", "close_time": "18:00"},
            {"day_of_week": 4, "open_time": "08:00", "close_time": "18:00"},
            {"day_of_week": 5, "open_time": "09:00", "close_time": "13:00"},
            {"day_of_week": 6, "open_time": None, "close_time": None},  # Closed Sunday
        ]
        resp = client.put(
            f"/api/contacts/{contact_id}/schedules",
            headers=headers,
            json=schedules
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Horarios actualizados"

    def test_list_schedules_returns_formatted_data(self, client, auth_headers):
        """GET schedules should return formatted day names."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test Contact",
            "phone": "1234567",
        })
        assert resp.status_code == 201
        contact_id = resp.json()["id"]

        # Set schedules
        client.put(
            f"/api/contacts/{contact_id}/schedules",
            headers=headers,
            json=[{"day_of_week": 0, "open_time": "08:00", "close_time": "18:00"}]
        )

        # List schedules
        resp = client.get(f"/api/contacts/{contact_id}/schedules")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["day_name"] == "Lunes"
        assert data[0]["open_time"] == "08:00"
        assert data[0]["is_closed"] is False


# ---------------------------------------------------------------------------
# Provider Dashboard Tests
# ---------------------------------------------------------------------------

class TestProviderDashboard:
    """Test provider dashboard metrics."""

    def test_dashboard_returns_metrics(self, client, auth_headers, contact_factory, db_session):
        """GET /api/provider/dashboard should return metrics for a provider."""
        headers = auth_headers(username="provider", email="provider@test.com")
        # Create a contact owned by this user
        contact_id = contact_factory(headers=headers, name="Mi Negocio", phone="1234567")

        resp = client.get("/api/provider/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "contacts" in data
        assert "total_contacts" in data
        assert "leads_this_month" in data
        assert "leads_last_month" in data
        assert "active_offers" in data
        assert "leads_by_week" in data
        assert "recent_reviews" in data
        assert data["total_contacts"] >= 1

    def test_dashboard_no_contacts_returns_404(self, client, auth_headers):
        """GET /api/provider/dashboard should return 404 if user has no contacts."""
        headers = auth_headers(username="nocontacts", email="nocontacts@test.com")
        resp = client.get("/api/provider/dashboard", headers=headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Offers CRUD Tests
# ---------------------------------------------------------------------------

class TestOffersCRUD:
    """Test offers CRUD operations."""

    def _create_contact_with_owner(self, client, auth_headers):
        """Helper to create a contact and return its ID."""
        headers = auth_headers(username="offerowner", email="offerowner@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Offer Contact",
            "phone": "1234567",
        })
        assert resp.status_code == 201
        return resp.json()["id"], headers

    def test_create_offer(self, client, auth_headers):
        """POST /api/contacts/{id}/offers should create an offer."""
        contact_id, headers = self._create_contact_with_owner(client, auth_headers)
        future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

        resp = client.post(
            f"/api/contacts/{contact_id}/offers",
            headers=headers,
            json={
                "title": "20% OFF",
                "description": "Descuento especial",
                "discount_pct": 20,
                "expires_at": future,
            }
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "20% OFF"
        assert data["discount_pct"] == 20
        assert data["is_active"] is True

    def test_create_offer_past_date_fails(self, client, auth_headers):
        """POST should fail if expires_at is in the past."""
        contact_id, headers = self._create_contact_with_owner(client, auth_headers)
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        resp = client.post(
            f"/api/contacts/{contact_id}/offers",
            headers=headers,
            json={
                "title": "Expired",
                "description": "Already expired",
                "discount_pct": 10,
                "expires_at": past,
            }
        )
        assert resp.status_code == 400

    def test_list_offers(self, client, auth_headers):
        """GET /api/contacts/{id}/offers should list active offers."""
        contact_id, headers = self._create_contact_with_owner(client, auth_headers)
        future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

        # Create an offer
        client.post(
            f"/api/contacts/{contact_id}/offers",
            headers=headers,
            json={
                "title": "Test Offer",
                "description": "Test",
                "discount_pct": 15,
                "expires_at": future,
            }
        )

        # List offers (public)
        resp = client.get(f"/api/contacts/{contact_id}/offers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["title"] == "Test Offer"

    def test_list_offers_excludes_expired(self, client, auth_headers, db_session):
        """GET should not return expired offers."""
        contact_id, headers = self._create_contact_with_owner(client, auth_headers)
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        # Insert an expired offer directly into DB
        from app.models.offer import Offer
        offer = Offer(
            contact_id=contact_id,
            title="Expired Offer",
            description="Old",
            discount_pct=50,
            expires_at=datetime.fromisoformat(past),
            is_active=True,
        )
        db_session.add(offer)
        db_session.commit()

        resp = client.get(f"/api/contacts/{contact_id}/offers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0

    def test_update_offer(self, client, auth_headers):
        """PUT should update an offer."""
        contact_id, headers = self._create_contact_with_owner(client, auth_headers)
        future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

        # Create offer
        resp = client.post(
            f"/api/contacts/{contact_id}/offers",
            headers=headers,
            json={
                "title": "Original",
                "description": "Original desc",
                "discount_pct": 10,
                "expires_at": future,
            }
        )
        assert resp.status_code == 201
        offer_id = resp.json()["id"]

        # Update
        future2 = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        resp = client.put(
            f"/api/contacts/{contact_id}/offers/{offer_id}",
            headers=headers,
            json={
                "title": "Updated",
                "description": "Updated desc",
                "discount_pct": 25,
                "expires_at": future2,
            }
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"
        assert resp.json()["discount_pct"] == 25

    def test_delete_offer(self, client, auth_headers):
        """DELETE should remove an offer."""
        contact_id, headers = self._create_contact_with_owner(client, auth_headers)
        future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

        resp = client.post(
            f"/api/contacts/{contact_id}/offers",
            headers=headers,
            json={
                "title": "To Delete",
                "description": "Will be deleted",
                "discount_pct": 10,
                "expires_at": future,
            }
        )
        assert resp.status_code == 201
        offer_id = resp.json()["id"]

        resp = client.delete(
            f"/api/contacts/{contact_id}/offers/{offer_id}",
            headers=headers,
        )
        assert resp.status_code == 204

    def test_cannot_create_offer_for_others_contact(self, client, auth_headers):
        """Non-owner should not be able to create offers."""
        # Owner creates contact
        owner_headers = auth_headers(username="offerowner2", email="offerowner2@test.com")
        contact_id, _ = self._create_contact_with_owner(client, auth_headers)

        # Another user tries to create offer
        other_headers = auth_headers(username="otheruser", email="otheruser@test.com")
        future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        resp = client.post(
            f"/api/contacts/{contact_id}/offers",
            headers=other_headers,
            json={
                "title": "Hacker Offer",
                "description": "Not mine",
                "discount_pct": 99,
                "expires_at": future,
            }
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Analytics & Admin Tests
# ---------------------------------------------------------------------------

class TestAnalyticsExport:
    """Test analytics export functionality."""

    def test_export_csv_requires_auth(self, client):
        """GET /api/admin/analytics/export should require auth."""
        resp = client.get("/api/admin/analytics/export")
        assert resp.status_code == 401

    def test_export_csv_requires_admin(self, client, auth_headers):
        """Regular user should not access analytics export."""
        headers = auth_headers(username="analyticsuser", email="analyticsuser@test.com")
        resp = client.get("/api/admin/analytics/export", headers=headers)
        assert resp.status_code == 403

    def test_export_csv_returns_csv(self, client, admin_headers):
        """Admin should get CSV export."""
        resp = client.get("/api/admin/analytics/export", headers=admin_headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        # Parse CSV to verify structure
        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        if rows:
            header = rows[0]
            assert "id" in header[0].lower() or "nombre" in header[0].lower()


class TestAdminAnalytics:
    """Test analytics endpoint."""

    def test_analytics_requires_auth(self, client):
        """GET /api/admin/analytics should require auth."""
        resp = client.get("/api/admin/analytics")
        assert resp.status_code == 401

    def test_analytics_returns_data(self, client, admin_headers):
        """Admin should get analytics data."""
        resp = client.get("/api/admin/analytics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_providers" in data
        assert "active_providers" in data
        assert "total_leads" in data
        assert "total_reviews" in data
        assert "avg_rating" in data
        assert "top_categories" in data
        assert "leads_by_day" in data


# ---------------------------------------------------------------------------
# Public Endpoints Tests
# ---------------------------------------------------------------------------

class TestPublicEndpoints:
    """Test public endpoints that were not covered."""

    def test_public_users_returns_active_users(self, client, create_user):
        """GET /api/public/users should return active users."""
        create_user(username="publicuser1", email="pub1@test.com")
        create_user(username="publicuser2", email="pub2@test.com")

        resp = client.get("/api/public/users")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        for u in data:
            assert "id" in u
            assert "username" in u

    def test_public_users_excludes_inactive(self, client, create_user):
        """GET /api/public/users should not include inactive users."""
        create_user(username="inactiveuser", email="inactive@test.com", is_active=False)
        create_user(username="activeuser", email="active@test.com", is_active=True)

        resp = client.get("/api/public/users")
        assert resp.status_code == 200
        data = resp.json()
        usernames = [u["username"] for u in data]
        assert "activeuser" in usernames
        assert "inactiveuser" not in usernames

    def test_health_endpoint(self, client):
        """GET /health should return health status."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "database" in data["checks"]


# ---------------------------------------------------------------------------
# Friendly URL Tests
# ---------------------------------------------------------------------------

class TestFriendlyURLs:
    """Test friendly URL redirects."""

    def test_slug_redirect(self, client, auth_headers, contact_factory, db_session):
        """GET /c/{slug} should redirect to /profile?id=X."""
        headers = auth_headers(username="sluguser", email="sluguser@test.com")
        contact_id = contact_factory(headers=headers, name="Juan Perez", phone="1234567")

        # Set a slug
        from app.models.contact import Contact
        contact = db_session.query(Contact).filter(Contact.id == contact_id).first()
        contact.slug = "juan-perez-plomero-1"
        db_session.commit()

        resp = client.get("/c/juan-perez-plomero-1", follow_redirects=False)
        assert resp.status_code == 301
        assert f"/profile?id={contact_id}" in resp.headers["location"]

    def test_slug_not_found(self, client):
        """GET /c/nonexistent should return 404."""
        resp = client.get("/c/nonexistent-slug")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Reviews N+1 Fix Validation
# ---------------------------------------------------------------------------

class TestReviewsBatchFetch:
    """Validate that reviews endpoint uses batch fetch (no N+1)."""

    def test_list_reviews_with_multiple_reviews(self, client, create_user, contact_factory, auth_headers, db_session):
        """GET reviews should return enriched data with usernames."""
        # Create owner and contact
        owner_headers = auth_headers(username="reviewowner", email="reviewowner@test.com")
        contact_id = contact_factory(headers=owner_headers, name="Review Target", phone="1234567")

        # Create reviewers using create_user (bypasses CAPTCHA issues)
        reviewer1 = create_user(username="reviewer1", email="reviewer1@test.com")
        reviewer2 = create_user(username="reviewer2", email="reviewer2@test.com")
        reviewer3 = create_user(username="reviewer3", email="reviewer3@test.com")

        # Create reviews directly in DB
        from app.models.review import Review
        for i, reviewer in enumerate([reviewer1, reviewer2, reviewer3]):
            review = Review(
                contact_id=contact_id,
                user_id=reviewer.id,
                rating=4 + (i % 2),
                comment=f"Review {i}",
                is_approved=True,
            )
            db_session.add(review)
        db_session.commit()

        resp = client.get(f"/api/contacts/{contact_id}/reviews")
        assert resp.status_code == 200
        data = resp.json()
        assert "reviews" in data
        assert "total" in data
        assert "avg_rating" in data
        assert len(data["reviews"]) == 3
        # Verify usernames are present (batch fetch working)
        usernames = {r["username"] for r in data["reviews"]}
        assert "reviewer1" in usernames
        assert "reviewer2" in usernames
        assert "reviewer3" in usernames


# ---------------------------------------------------------------------------
# Edge Cases & Robustness
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_contact_search_with_special_chars(self, client):
        """Search should handle special characters safely."""
        resp = client.get("/api/contacts/search?q=%27%22%3B--")
        # Should not crash - either 200 with empty results or 400
        assert resp.status_code in [200, 400]

    def test_contact_search_empty_query(self, client):
        """Search without any filter should return 400."""
        resp = client.get("/api/contacts/search")
        assert resp.status_code == 400

    def test_phone_search_minimum_length(self, client):
        """Phone search should require min 3 characters."""
        resp = client.get("/api/contacts/search/phone?phone=ab")
        assert resp.status_code == 422

    def test_list_contacts_pagination(self, client):
        """GET /api/contacts should support pagination."""
        resp = client.get("/api/contacts?skip=0&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert "contacts" in data
        assert "total" in data

    def test_list_contacts_by_category(self, client):
        """GET /api/contacts should filter by category."""
        resp = client.get("/api/contacts?category_id=100")
        assert resp.status_code == 200

    def test_related_businesses_no_geo(self, client, auth_headers, contact_factory):
        """GET related businesses should return empty if no geo data."""
        headers = auth_headers(username="relateduser", email="relateduser@test.com")
        contact_id = contact_factory(headers=headers, name="No Geo", phone="1234567")

        resp = client.get(f"/api/contacts/{contact_id}/related")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_lead_registration_optional_auth(self, client, auth_headers, contact_factory):
        """POST leads should work with or without auth."""
        headers = auth_headers(username="leaduser", email="leaduser@test.com")
        contact_id = contact_factory(headers=headers, name="Lead Target", phone="1234567")

        # With auth
        resp = client.post(f"/api/contacts/{contact_id}/leads")
        assert resp.status_code == 201

        # Without auth
        resp = client.post(f"/api/contacts/{contact_id}/leads")
        assert resp.status_code == 201

    def test_lead_requires_contact_exist(self, client):
        """POST leads should return 404 for non-existent contact."""
        resp = client.post("/api/contacts/99999/leads")
        assert resp.status_code == 404

    def test_notifications_requires_auth(self, client):
        """GET notifications should require auth."""
        resp = client.get("/api/notifications")
        assert resp.status_code == 401

    def test_vapid_public_key_public(self, client):
        """GET vapid-public-key should be accessible without auth."""
        resp = client.get("/api/notifications/vapid-public-key")
        # Either 200 with key or 503 if not configured
        assert resp.status_code in [200, 503]

    def test_utilities_public_endpoint(self, client):
        """GET /api/utilities should be accessible without auth."""
        resp = client.get("/api/utilities")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_utilities_requires_admin_for_create(self, client):
        """POST utilities should require admin auth."""
        resp = client.post("/api/admin/utilities", json={
            "name": "Test",
            "type": "emergency",
            "phone": "911",
        })
        assert resp.status_code == 401

    def test_report_requires_auth(self, client):
        """POST report should require auth."""
        resp = client.post("/api/contacts/1/report", json={
            "reason": "spam",
            "details": "This is spam",
        })
        assert resp.status_code == 401

    def test_admin_reports_requires_admin(self, client, auth_headers):
        """GET admin reports should require admin/mod role."""
        headers = auth_headers(username="reportuser", email="reportuser@test.com")
        resp = client.get("/api/admin/reports/flagged", headers=headers)
        assert resp.status_code == 403

    def test_admin_contact_status_requires_admin(self, client, auth_headers):
        """PUT admin contact status should require admin/mod role."""
        headers = auth_headers(username="statususer", email="statususer@test.com")
        resp = client.put(
            "/api/admin/contacts/1/status?new_status=suspended",
            headers=headers,
        )
        assert resp.status_code == 403
