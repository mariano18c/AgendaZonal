"""Targeted integration tests to fill remaining coverage gaps."""
import pytest
import csv
import io
from datetime import datetime, timezone, timedelta

from app.models.contact import Contact
from app.models.lead_event import LeadEvent
from app.models.review import Review
from app.models.report import Report
from app.models.contact_change import ContactChange
from app.models.utility_item import UtilityItem


# ===========================================================================
# ADMIN - Analytics & Reports (fills admin.py gaps)
# ===========================================================================

class TestAdminAnalytics:
    """Test admin analytics endpoints."""

    def test_analytics_returns_data(self, client, admin_headers, create_contact, db_session):
        """Admin can view analytics with data."""
        contact = create_contact(name="Analytics Biz")
        # Add some leads
        db_session.add(LeadEvent(contact_id=contact.id, source="whatsapp"))
        db_session.add(LeadEvent(contact_id=contact.id, source="web"))
        db_session.commit()

        resp = client.get("/api/admin/analytics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_export_analytics_csv(self, client, admin_headers, create_contact, db_session):
        """Admin can export analytics as CSV."""
        contact = create_contact(name="Export Biz")
        db_session.add(LeadEvent(contact_id=contact.id, source="whatsapp"))
        db_session.commit()

        resp = client.get("/api/admin/analytics/export", headers=admin_headers)
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "csv" in content_type.lower() or "text" in content_type.lower()

    def test_export_analytics_has_csv_content(self, client, admin_headers, create_contact, db_session):
        """Exported CSV should have valid content."""
        contact = create_contact(name="CSV Export")
        db_session.add(LeadEvent(contact_id=contact.id, source="whatsapp"))
        db_session.commit()

        resp = client.get("/api/admin/analytics/export", headers=admin_headers)
        assert resp.status_code == 200
        # Parse CSV
        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        assert len(rows) > 0

    def test_analytics_requires_mod_role(self, client, moderator_user):
        """Moderator can access analytics."""
        _, headers = moderator_user
        resp = client.get("/api/admin/analytics", headers=headers)
        assert resp.status_code == 200


class TestAdminReports:
    """Test admin report management."""

    def test_list_flagged_contacts(self, client, admin_headers, create_contact, db_session):
        """Admin can list flagged contacts."""
        contact = create_contact(name="Flagged Biz", status="flagged")
        db_session.commit()

        resp = client.get("/api/admin/reports/flagged", headers=admin_headers)
        assert resp.status_code == 200

    def test_list_pending_reports(self, client, admin_headers, create_contact, create_report):
        """Admin can list pending reports."""
        contact = create_contact(name="Pending Report")
        create_report(contact_id=contact.id, reason="spam")

        resp = client.get("/api/admin/reports/pending", headers=admin_headers)
        assert resp.status_code == 200

    def test_resolve_report(self, client, admin_headers, create_contact, create_report, db_session):
        """Admin can resolve a report with an action."""
        contact = create_contact(name="Resolve Test")
        report = create_report(contact_id=contact.id, reason="falso")

        resp = client.post(f"/api/admin/reports/{report.id}/resolve?action=suspend", headers=admin_headers)
        assert resp.status_code == 200

        # Verify resolved in DB
        db_session.refresh(report)
        assert report.is_resolved is True


class TestAdminContactStatus:
    """Test admin contact status management."""

    def test_update_contact_status(self, client, admin_headers, create_contact, db_session):
        """Admin can update contact status."""
        contact = create_contact(name="Status Update")

        resp = client.put(f"/api/admin/contacts/{contact.id}/status?new_status=suspended", headers=admin_headers)
        assert resp.status_code == 200

        db_session.refresh(contact)
        assert contact.status == "suspended"

        db_session.refresh(contact)
        assert contact.status == "suspended"

    def test_list_admin_contacts(self, client, admin_headers, create_contact):
        """Admin can list all contacts."""
        create_contact(name="Admin List 1")
        create_contact(name="Admin List 2")

        resp = client.get("/api/admin/contacts", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "contacts" in data or isinstance(data, list)


# ===========================================================================
# ADMIN - Utilities (fills remaining utility gaps)
# ===========================================================================

class TestAdminUtilitiesFull:
    """Test utility CRUD via admin endpoints."""

    def test_list_utilities_empty(self, client):
        """List utilities when none exist."""
        resp = client.get("/api/utilities")
        assert resp.status_code == 200

    def test_create_utility_moderator(self, client, moderator_user):
        """Moderator can create utility items."""
        _, headers = moderator_user
        resp = client.post("/api/admin/utilities", headers=headers, json={
            "name": "Farmacia Central",
            "type": "salud",
            "phone": "0341-4801234",
            "address": "San Martín 1234",
            "city": "Rosario",
        })
        assert resp.status_code == 201

    def test_update_utility_moderator(self, client, moderator_user, create_utility):
        """Moderator can update utility items."""
        _, headers = moderator_user
        utility = create_utility(name="Old Utility")

        resp = client.put(f"/api/admin/utilities/{utility.id}", headers=headers, json={
            "name": "Updated Utility",
            "phone": "9999999",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Utility"

    def test_delete_utility_moderator(self, client, moderator_user, create_utility):
        """Moderator can delete utility items."""
        _, headers = moderator_user
        utility = create_utility(name="Delete Me")

        resp = client.delete(f"/api/admin/utilities/{utility.id}", headers=headers)
        assert resp.status_code == 204


# ===========================================================================
# REVIEWS - Moderation (fills review.py gaps)
# ===========================================================================

class TestReviewModerationFull:
    """Test review moderation endpoints."""

    def test_approve_review_admin(self, client, admin_headers, create_contact, create_review):
        """Admin can approve a review."""
        contact = create_contact(name="Approve Admin")
        review = create_review(contact_id=contact.id, rating=5, comment="Great!", is_approved=False)

        resp = client.post(f"/api/admin/reviews/{review.id}/approve", headers=admin_headers)
        assert resp.status_code == 200

    def test_reject_review_admin(self, client, admin_headers, create_contact, create_review):
        """Admin can reject a review."""
        contact = create_contact(name="Reject Admin")
        review = create_review(contact_id=contact.id, rating=1, comment="Terrible", is_approved=False)

        resp = client.post(f"/api/admin/reviews/{review.id}/reject", headers=admin_headers)
        assert resp.status_code == 200

    def test_set_verification_level(self, client, admin_headers, create_contact):
        """Admin can set verification level on a contact."""
        contact = create_contact(name="Verify Level")

        resp = client.put(f"/api/admin/contacts/{contact.id}/verification", headers=admin_headers, json={
            "verification_level": 3,
        })
        assert resp.status_code == 200

    def test_reply_to_review(self, client, auth_headers, db_session):
        """Contact owner can reply to a review."""
        from app.models.user import User
        from tests.conftest import _hash_password

        owner = User(
            username="reply_owner2", email="reply_owner2@test.com",
            phone_area_code="0341", phone_number="1234567",
            password_hash=_hash_password("password123"),
        )
        db_session.add(owner)
        db_session.commit()
        db_session.refresh(owner)

        contact = Contact(name="Reply Biz", phone="123", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        reviewer = User(
            username="reply_reviewer2", email="reply_reviewer2@test.com",
            phone_area_code="0341", phone_number="7654321",
            password_hash=_hash_password("password123"),
        )
        db_session.add(reviewer)
        db_session.commit()
        db_session.refresh(reviewer)

        review = Review(
            contact_id=contact.id, user_id=reviewer.id,
            rating=4, comment="Good service", is_approved=True,
        )
        db_session.add(review)
        db_session.commit()
        db_session.refresh(review)

        from app.auth import create_token
        token = create_token(owner.id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        resp = client.post(f"/api/reviews/{review.id}/reply", headers=owner_headers, json={
            "reply_text": "Thank you!",
        })
        assert resp.status_code == 200


# ===========================================================================
# OFFERS - Full CRUD (fills offers.py gaps)
# ===========================================================================

class TestOffersFull:
    """Test offer CRUD endpoints."""

    def test_list_offers_empty(self, client, create_contact):
        """List offers when none exist."""
        contact = create_contact(name="No Offers")
        resp = client.get(f"/api/contacts/{contact.id}/offers")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_offer_past_expiry(self, client, auth_headers):
        """Creating offer with past expiry should be handled."""
        headers = auth_headers(username="offer_past2", email="offer_past2@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Past Offer",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        owner_id = create_resp.json()["user_id"]

        from app.auth import create_token
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        resp = client.post(f"/api/contacts/{cid}/offers", headers=owner_headers, json={
            "title": "Expired",
            "discount_pct": 50,
            "expires_at": past,
        })
        # May accept or reject depending on implementation
        assert resp.status_code in [201, 400, 422]

    def test_update_offer_nonexistent(self, client, auth_headers):
        """Update non-existent offer should return 404."""
        headers = auth_headers(username="offer_upd404", email="offer_upd404@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Update 404",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        owner_id = create_resp.json()["user_id"]

        from app.auth import create_token
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        resp = client.put(f"/api/contacts/{cid}/offers/999999", headers=owner_headers, json={
            "title": "Nope",
            "discount_pct": 10,
            "expires_at": future,
        })
        assert resp.status_code == 404

    def test_delete_offer_nonexistent(self, client, auth_headers):
        """Delete non-existent offer should return 404."""
        headers = auth_headers(username="offer_del404", email="offer_del404@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Delete 404",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        owner_id = create_resp.json()["user_id"]

        from app.auth import create_token
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        resp = client.delete(f"/api/contacts/{cid}/offers/999999", headers=owner_headers)
        assert resp.status_code == 404


# ===========================================================================
# PROVIDER - Dashboard (fills provider.py gaps)
# ===========================================================================

class TestProviderDashboardFull:
    """Test provider dashboard with data."""

    def test_dashboard_with_contacts(self, client, auth_headers):
        """Dashboard should return metrics when user has contacts."""
        headers = auth_headers(username="dash_full", email="dash_full@test.com")
        client.post("/api/contacts", headers=headers, json={
            "name": "Dashboard Biz",
            "phone": "1234567",
        })

        resp = client.get("/api/provider/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)


# ===========================================================================
# AUTH - Bootstrap admin edge cases (fills auth.py gaps)
# ===========================================================================

class TestAuthBootstrapEdgeCases:
    """Test bootstrap-admin edge cases."""

    def test_bootstrap_fails_when_users_exist(self, client, captcha, create_user):
        """Bootstrap should fail when users already exist."""
        create_user(username="existing_user", email="existing@test.com")

        resp = client.post("/api/auth/bootstrap-admin", json={
            "username": "late_admin",
            "email": "late@admin.com",
            "phone_area_code": "0341",
            "phone_number": "1111111",
            "password": "adminpass123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        assert resp.status_code == 403
