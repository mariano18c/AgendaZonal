"""Integration tests — Reviews, Offers, Reports, Notifications, Provider, Admin, Users."""
import pytest
from datetime import datetime, timezone, timedelta

from app.models.review import Review
from app.models.offer import Offer
from app.models.report import Report
from app.models.notification import Notification
from app.models.contact import Contact


# ===========================================================================
# REVIEWS
# ===========================================================================

class TestReviewCreate:
    """Test review creation flow."""

    def test_create_review_success(self, client, auth_headers, create_contact):
        """Authenticated user can create a review."""
        headers = auth_headers(username="rev1", email="rev1@test.com")
        contact = create_contact(name="Review Target")

        resp = client.post(f"/api/contacts/{contact.id}/reviews", headers=headers, json={
            "rating": 5,
            "comment": "Excellent service!",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["rating"] == 5

    def test_create_review_requires_auth(self, client, create_contact):
        """Unauthenticated user cannot create review."""
        contact = create_contact(name="No Auth Review")
        resp = client.post(f"/api/contacts/{contact.id}/reviews", json={
            "rating": 4,
            "comment": "Good",
        })
        assert resp.status_code == 401

    def test_create_review_invalid_rating(self, client, auth_headers, create_contact):
        """Rating out of 1-5 range should be rejected."""
        headers = auth_headers(username="rev2", email="rev2@test.com")
        contact = create_contact(name="Bad Rating")

        resp = client.post(f"/api/contacts/{contact.id}/reviews", headers=headers, json={
            "rating": 6,
            "comment": "Too high",
        })
        assert resp.status_code == 422

    def test_create_review_duplicate_rejected(self, client, auth_headers, create_contact):
        """Same user cannot review same contact twice."""
        headers = auth_headers(username="rev3", email="rev3@test.com")
        contact = create_contact(name="Dup Review")

        resp1 = client.post(f"/api/contacts/{contact.id}/reviews", headers=headers, json={
            "rating": 5,
            "comment": "First",
        })
        assert resp1.status_code == 201

        resp2 = client.post(f"/api/contacts/{contact.id}/reviews", headers=headers, json={
            "rating": 3,
            "comment": "Second",
        })
        assert resp2.status_code == 409

    def test_create_review_persists_to_db(self, client, auth_headers, create_contact, db_session):
        """Review should be queryable in DB."""
        headers = auth_headers(username="rev4", email="rev4@test.com")
        contact = create_contact(name="DB Review")

        client.post(f"/api/contacts/{contact.id}/reviews", headers=headers, json={
            "rating": 4,
            "comment": "Persisted",
        })

        review = db_session.query(Review).filter(
            Review.contact_id == contact.id,
            Review.comment == "Persisted",
        ).first()
        assert review is not None
        assert review.rating == 4
        assert review.is_approved is False  # Not approved by default


class TestReviewList:
    """Test review listing."""

    def test_list_approved_reviews(self, client, create_contact, create_review):
        """Only approved reviews should be listed publicly."""
        contact = create_contact(name="Review List")
        create_review(contact_id=contact.id, rating=5, comment="Approved", is_approved=True)
        create_review(contact_id=contact.id, rating=3, comment="Pending", is_approved=False)

        resp = client.get(f"/api/contacts/{contact.id}/reviews")
        assert resp.status_code == 200
        data = resp.json()
        # Only approved reviews
        comments = [r["comment"] for r in data["reviews"]]
        assert "Approved" in comments
        assert "Pending" not in comments

    def test_list_reviews_empty(self, client, create_contact):
        """Contact with no reviews should return empty list."""
        contact = create_contact(name="No Reviews")
        resp = client.get(f"/api/contacts/{contact.id}/reviews")
        assert resp.status_code == 200
        assert resp.json()["reviews"] == []

    def test_list_reviews_nonexistent_contact(self, client):
        """Reviews for non-existent contact should return 404."""
        resp = client.get("/api/contacts/999999/reviews")
        assert resp.status_code == 404


class TestReviewModeration:
    """Test review moderation (approve/reject/reply)."""

    def test_approve_review_moderator(self, client, moderator_user, create_contact, create_review):
        """Moderator can approve a review."""
        _, mod_headers = moderator_user
        contact = create_contact(name="Mod Review")
        review = create_review(contact_id=contact.id, rating=4, comment="Needs approval")

        resp = client.post(f"/api/admin/reviews/{review.id}/approve", headers=mod_headers)
        assert resp.status_code == 200

    def test_reject_review_moderator(self, client, moderator_user, create_contact, create_review):
        """Moderator can reject a review."""
        _, mod_headers = moderator_user
        contact = create_contact(name="Reject Review")
        review = create_review(contact_id=contact.id, rating=2, comment="Bad review")

        resp = client.post(f"/api/admin/reviews/{review.id}/reject", headers=mod_headers)
        assert resp.status_code == 200

    def test_reply_to_review_owner(self, client, db_session, auth_headers):
        """Contact owner can reply to a review."""
        from app.auth import create_token
        from tests.conftest import _hash_password
        from app.models.user import User

        owner = User(
            username="reply_owner", email="reply_owner@test.com",
            phone_area_code="0341", phone_number="1234567",
            password_hash=_hash_password("password123"),
        )
        db_session.add(owner)
        db_session.commit()
        db_session.refresh(owner)

        contact = Contact(name="Reply Test", phone="123", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        # Create an approved review
        reviewer = User(
            username="reply_reviewer", email="reply_reviewer@test.com",
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

        # Owner replies
        token = create_token(owner.id)
        owner_headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(f"/api/reviews/{review.id}/reply", headers=owner_headers, json={
            "reply_text": "Thank you for your feedback!",
        })
        assert resp.status_code == 200

    def test_list_pending_reviews_moderator(self, client, moderator_user, create_contact, create_review):
        """Moderator can list pending reviews."""
        _, mod_headers = moderator_user
        contact = create_contact(name="Pending List")
        create_review(contact_id=contact.id, rating=3, comment="Pending 1", is_approved=False)
        create_review(contact_id=contact.id, rating=5, comment="Pending 2", is_approved=False)

        resp = client.get("/api/admin/reviews/pending", headers=mod_headers)
        assert resp.status_code == 200

    def test_regular_user_cannot_moderate(self, client, auth_headers, create_contact, create_review):
        """Regular user cannot approve/reject reviews."""
        headers = auth_headers(username="no_mod", email="no_mod@test.com")
        contact = create_contact(name="No Mod")
        review = create_review(contact_id=contact.id, rating=3, comment="Test")

        resp = client.post(f"/api/admin/reviews/{review.id}/approve", headers=headers)
        assert resp.status_code == 403


# ===========================================================================
# OFFERS
# ===========================================================================

class TestOfferCRUD:
    """Test offer lifecycle."""

    def test_create_offer(self, client, auth_headers):
        """Owner can create an offer for their contact."""
        headers = auth_headers(username="offer1", email="offer1@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Offer Biz",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        owner_id = create_resp.json()["user_id"]

        from app.auth import create_token
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        resp = client.post(f"/api/contacts/{cid}/offers", headers=owner_headers, json={
            "title": "Summer Sale",
            "description": "20% off",
            "discount_pct": 20,
            "expires_at": expires,
        })
        assert resp.status_code == 201
        assert resp.json()["title"] == "Summer Sale"

    def test_list_offers_public(self, client, create_contact, create_offer):
        """Anyone can list active offers for a contact."""
        contact = create_contact(name="Offer List")
        create_offer(contact_id=contact.id, title="Active Offer", is_active=True)

        resp = client.get(f"/api/contacts/{contact.id}/offers")
        assert resp.status_code == 200
        results = resp.json()
        assert any(o["title"] == "Active Offer" for o in results)

    def test_update_offer_owner(self, client, auth_headers):
        """Owner can update their offer."""
        headers = auth_headers(username="offer2", email="offer2@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Offer Update",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        owner_id = create_resp.json()["user_id"]

        from app.auth import create_token
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        create_resp = client.post(f"/api/contacts/{cid}/offers", headers=owner_headers, json={
            "title": "Original",
            "discount_pct": 10,
            "expires_at": expires,
        })
        oid = create_resp.json()["id"]

        resp = client.put(f"/api/contacts/{cid}/offers/{oid}", headers=owner_headers, json={
            "title": "Updated",
            "discount_pct": 30,
            "expires_at": expires,
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

    def test_delete_offer_owner(self, client, auth_headers):
        """Owner can delete their offer."""
        headers = auth_headers(username="offer3", email="offer3@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Offer Delete",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        owner_id = create_resp.json()["user_id"]

        from app.auth import create_token
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        create_resp = client.post(f"/api/contacts/{cid}/offers", headers=owner_headers, json={
            "title": "ToDelete",
            "discount_pct": 15,
            "expires_at": expires,
        })
        oid = create_resp.json()["id"]

        resp = client.delete(f"/api/contacts/{cid}/offers/{oid}", headers=owner_headers)
        assert resp.status_code == 200


# ===========================================================================
# REPORTS
# ===========================================================================

class TestReportFlow:
    """Test report creation and resolution."""

    def test_report_contact(self, client, auth_headers, create_contact):
        """User can report a contact they don't own."""
        headers = auth_headers(username="report1", email="report1@test.com")
        contact = create_contact(name="Report Target")

        resp = client.post(f"/api/contacts/{contact.id}/report", headers=headers, json={
            "reason": "spam",
            "details": "This is spam",
        })
        assert resp.status_code == 201

    def test_cannot_report_own_contact(self, client, auth_headers):
        """User cannot report their own contact."""
        headers = auth_headers(username="report2", email="report2@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "My Biz",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]

        resp = client.post(f"/api/contacts/{cid}/report", headers=headers, json={
            "reason": "spam",
        })
        assert resp.status_code == 400

    def test_cannot_report_twice(self, client, auth_headers, create_contact):
        """User cannot report the same contact twice."""
        headers = auth_headers(username="report3", email="report3@test.com")
        contact = create_contact(name="Double Report")

        client.post(f"/api/contacts/{contact.id}/report", headers=headers, json={
            "reason": "spam",
        })

        resp = client.post(f"/api/contacts/{contact.id}/report", headers=headers, json={
            "reason": "falso",
        })
        assert resp.status_code == 409

    def test_auto_flag_at_threshold(self, client, create_contact, db_session):
        """Contact should be auto-flagged after 3 distinct reports."""
        contact = create_contact(name="Auto Flag", status="active")

        from tests.conftest import _hash_password
        from app.models.user import User
        for i in range(3):
            user = User(
                username=f"flagger_{i}", email=f"flagger_{i}@test.com",
                phone_area_code="0341", phone_number=f"555555{i}",
                password_hash=_hash_password("password123"),
            )
            db_session.add(user)
        db_session.commit()

        reporters = db_session.query(User).filter(User.username.like("flagger_%")).all()
        for reporter in reporters:
            report = Report(
                contact_id=contact.id, user_id=reporter.id,
                reason="spam", is_resolved=False,
            )
            db_session.add(report)
        db_session.commit()

        # Refresh contact
        db_session.refresh(contact)
        assert contact.status == "flagged"

    def test_resolve_report_moderator(self, client, moderator_user, create_contact, create_report):
        """Moderator can resolve a report."""
        _, mod_headers = moderator_user
        contact = create_contact(name="Resolve Report")
        report = create_report(contact_id=contact.id, reason="spam")

        resp = client.post(f"/api/admin/reports/{report.id}/resolve", headers=mod_headers)
        assert resp.status_code == 200


# ===========================================================================
# NOTIFICATIONS
# ===========================================================================

class TestNotifications:
    """Test notification endpoints."""

    def test_list_notifications(self, client, create_user, create_notification):
        """User can list their notifications."""
        user = create_user(username="notif1", email="notif1@test.com")
        create_notification(user_id=user.id, message="Test notification")

        from app.auth import create_token
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/notifications", headers=headers)
        assert resp.status_code == 200
        results = resp.json()
        assert any(n["message"] == "Test notification" for n in results)

    def test_cannot_view_others_notifications(self, client, create_user, create_notification):
        """User cannot see other user's notifications."""
        user1 = create_user(username="victim_notif", email="victim_n@test.com")
        user2 = create_user(username="attacker_notif", email="attacker_n@test.com")

        create_notification(user_id=user1.id, message="Secret data")

        from app.auth import create_token
        token = create_token(user2.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/notifications", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_mark_notification_read(self, client, create_user, create_notification):
        """User can mark their notification as read."""
        user = create_user(username="notif2", email="notif2@test.com")
        notif = create_notification(user_id=user.id, message="Read me", is_read=False)

        from app.auth import create_token
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.put(f"/api/notifications/{notif.id}/read", headers=headers)
        assert resp.status_code == 200

    def test_mark_all_read(self, client, create_user, create_notification):
        """User can mark all notifications as read."""
        user = create_user(username="notif3", email="notif3@test.com")
        create_notification(user_id=user.id, message="Notif 1", is_read=False)
        create_notification(user_id=user.id, message="Notif 2", is_read=False)

        from app.auth import create_token
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.put("/api/notifications/read-all", headers=headers)
        assert resp.status_code == 200

    def test_vapid_public_key(self, client):
        """VAPID public key endpoint should be accessible."""
        resp = client.get("/api/notifications/vapid-public-key")
        # May return 200 with key or 200 with null if not configured
        assert resp.status_code == 200


# ===========================================================================
# PROVIDER DASHBOARD
# ===========================================================================

class TestProviderDashboard:
    """Test provider dashboard metrics."""

    def test_dashboard_requires_auth(self, client):
        """Dashboard should require authentication."""
        resp = client.get("/api/provider/dashboard")
        assert resp.status_code == 401

    def test_dashboard_returns_metrics(self, client, auth_headers):
        """Dashboard should return metrics for authenticated user."""
        headers = auth_headers(username="dash1", email="dash1@test.com")
        resp = client.get("/api/provider/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "contacts" in data or "total_contacts" in data or isinstance(data, dict)


# ===========================================================================
# ADMIN
# ===========================================================================

class TestAdminEndpoints:
    """Test admin-only endpoints."""

    def test_admin_analytics(self, client, admin_headers):
        """Admin can access analytics."""
        resp = client.get("/api/admin/analytics", headers=admin_headers)
        assert resp.status_code == 200

    def test_admin_analytics_requires_admin(self, client, auth_headers):
        """Non-admin cannot access analytics."""
        headers = auth_headers(username="no_admin", email="no_admin@test.com")
        resp = client.get("/api/admin/analytics", headers=headers)
        assert resp.status_code == 403

    def test_admin_flagged_contacts(self, client, admin_headers):
        """Admin can list flagged contacts."""
        resp = client.get("/api/admin/reports/flagged", headers=admin_headers)
        assert resp.status_code == 200

    def test_admin_pending_reports(self, client, admin_headers):
        """Admin can list pending reports."""
        resp = client.get("/api/admin/reports/pending", headers=admin_headers)
        assert resp.status_code == 200

    def test_admin_export_analytics(self, client, admin_headers):
        """Admin can export analytics as CSV."""
        resp = client.get("/api/admin/analytics/export", headers=admin_headers)
        assert resp.status_code == 200
        # Should be CSV
        assert "text/csv" in resp.headers.get("content-type", "")


# ===========================================================================
# USERS ADMIN
# ===========================================================================

class TestUserAdmin:
    """Test user management (admin only)."""

    def test_list_users_admin(self, client, admin_headers):
        """Admin can list all users."""
        resp = client.get("/api/users", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data

    def test_list_users_requires_admin(self, client, auth_headers):
        """Non-admin cannot list users."""
        headers = auth_headers(username="no_admin2", email="no_admin2@test.com")
        resp = client.get("/api/users", headers=headers)
        assert resp.status_code == 403

    def test_create_user_admin(self, client, admin_headers):
        """Admin can create a new user."""
        resp = client.post("/api/users", headers=admin_headers, json={
            "username": "new_admin_user",
            "email": "new_admin_user@test.com",
            "phone_area_code": "0341",
            "phone_number": "9999999",
            "password": "securepass123",
            "role": "user",
        })
        assert resp.status_code == 201

    def test_update_user_role_admin(self, client, admin_headers, create_user):
        """Admin can update user role."""
        user = create_user(username="role_change", email="role@test.com")
        resp = client.put(f"/api/users/{user.id}/role", headers=admin_headers, json={
            "role": "moderator",
        })
        assert resp.status_code == 200

    def test_deactivate_user_admin(self, client, admin_headers, create_user):
        """Admin can deactivate a user."""
        user = create_user(username="deact_admin", email="deact_admin@test.com")
        resp = client.delete(f"/api/users/{user.id}", headers=admin_headers)
        assert resp.status_code == 200

    def test_activate_user_admin(self, client, admin_headers, create_user):
        """Admin can activate a deactivated user."""
        user = create_user(username="activate_me", email="activate@test.com", is_active=False)
        resp = client.post(f"/api/users/{user.id}/activate", headers=admin_headers)
        assert resp.status_code == 200

    def test_reset_password_admin(self, client, admin_headers, create_user):
        """Admin can reset a user's password."""
        user = create_user(username="reset_me", email="reset@test.com")
        resp = client.post(f"/api/users/{user.id}/reset-password", headers=admin_headers, json={
            "new_password": "newSecurePass123!",
        })
        assert resp.status_code == 200


# ===========================================================================
# UTILITIES
# ===========================================================================

class TestUtilities:
    """Test utility items CRUD."""

    def test_list_utilities_public(self, client, create_utility):
        """Anyone can list utilities."""
        create_utility(name="Escuela Primaria", type="educacion")
        resp = client.get("/api/utilities")
        assert resp.status_code == 200
        results = resp.json()
        assert any(u["name"] == "Escuela Primaria" for u in results)

    def test_create_utility_admin(self, client, admin_headers):
        """Admin can create utility items."""
        resp = client.post("/api/admin/utilities", headers=admin_headers, json={
            "name": "Hospital Zonal",
            "type": "salud",
            "phone": "0341-4801234",
            "address": "Av. Pellegrini 1234",
            "city": "Rosario",
        })
        assert resp.status_code == 201

    def test_update_utility_admin(self, client, create_utility, admin_headers):
        """Admin can update utility items."""
        utility = create_utility(name="Old Name")
        resp = client.put(f"/api/admin/utilities/{utility.id}", headers=admin_headers, json={
            "name": "Updated Name",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    def test_delete_utility_admin(self, client, create_utility, admin_headers):
        """Admin can delete utility items."""
        utility = create_utility(name="To Delete")
        resp = client.delete(f"/api/admin/utilities/{utility.id}", headers=admin_headers)
        assert resp.status_code == 200

    def test_create_utility_requires_auth(self, client):
        """Unauthenticated user cannot create utilities."""
        resp = client.post("/api/admin/utilities", json={
            "name": "No Auth",
            "type": "otro",
        })
        assert resp.status_code == 401


# ===========================================================================
# CATEGORIES
# ===========================================================================

class TestCategories:
    """Test category listing."""

    def test_list_categories(self, client):
        """GET /api/categories should return all categories."""
        resp = client.get("/api/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert any(c["code"] == 100 for c in data)  # Plomero/a


# ===========================================================================
# PUBLIC ENDPOINTS
# ===========================================================================

class TestPublicEndpoints:
    """Test public endpoints."""

    def test_public_users_list(self, client, create_user):
        """GET /api/public/users should return active users."""
        create_user(username="public1", email="public1@test.com")
        resp = client.get("/api/public/users")
        assert resp.status_code == 200
        data = resp.json()
        assert any(u["username"] == "public1" for u in data)

    def test_health_check(self, client):
        """GET /health should return status ok."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "database" in data["checks"]


# ===========================================================================
# LEADS
# ===========================================================================

class TestLeads:
    """Test lead registration."""

    def test_register_lead_public(self, client, create_contact):
        """Anyone can register a lead (WhatsApp click)."""
        contact = create_contact(name="Lead Target")
        resp = client.post(f"/api/contacts/{contact.id}/leads", json={
            "source": "whatsapp",
        })
        assert resp.status_code == 201

    def test_get_leads_owner(self, client, auth_headers):
        """Owner can view leads for their contact."""
        headers = auth_headers(username="lead1", email="lead1@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Lead Biz",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]

        # Register some leads
        client.post(f"/api/contacts/{cid}/leads", json={"source": "whatsapp"})
        client.post(f"/api/contacts/{cid}/leads", json={"source": "web"})

        owner_id = create_resp.json()["user_id"]
        from app.auth import create_token
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        resp = client.get(f"/api/contacts/{cid}/leads", headers=owner_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2
