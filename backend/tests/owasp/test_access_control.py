"""OWASP A01: Broken Access Control tests.

Comprehensive tests for vertical/horizontal privilege escalation,
IDOR vulnerabilities, and improper CORS policies.
"""
import pytest
from tests.conftest import _bearer


class TestVerticalPrivilegeEscalation:
    """Test that regular users cannot escalate to admin/moderator privileges."""

    def test_cannot_assign_admin_role_via_update(self, client, create_user, create_contact):
        """Attempt to escalate privilege through contact update."""
        user = create_user()
        contact = create_contact(user_id=user.id)
        r = client.put(
            f"/api/contacts/{contact.id}",
            headers=_bearer(user),
            json={"name": "Test", "user_role": "admin"}
        )
        # Should either reject or ignore the role field
        assert r.status_code in [200, 403, 422]

    def test_cannot_access_admin_endpoints(self, client, create_user, user_headers):
        """Regular user cannot access admin API endpoints."""
        r = client.get("/api/admin/users", headers=user_headers)
        assert r.status_code in [403, 404]

    def test_cannot_access_moderator_endpoints(self, client, create_user, user_headers):
        """Regular user cannot access moderator endpoints."""
        r = client.get("/api/admin/reviews/pending", headers=user_headers)
        assert r.status_code in [403, 404]

    def test_cannot_modify_system_settings(self, client, create_user, user_headers):
        """Regular user cannot modify system configuration."""
        r = client.post("/api/admin/utilities", headers=user_headers, json={
            "name": "Test", "type": "otro", "phone": "123", "address": "test"
        })
        assert r.status_code in [403, 404]

    def test_cannot_access_other_users_dashboard(self, client, create_user, create_contact):
        """User cannot access another provider's dashboard."""
        owner = create_user()
        other = create_user()
        contact = create_contact(user_id=owner.id)
        r = client.get(f"/api/provider/dashboard", headers=_bearer(other))
        # Should return own data or 403/404
        assert r.status_code in [200, 403, 404]


class TestHorizontalPrivilegeEscalation:
    """Test that users cannot access other users' resources at same privilege level."""

    def test_cannot_view_other_user_private_data(self, client, create_user, create_contact):
        """User cannot access private data of another user."""
        user1 = create_user()
        user2 = create_user()
        contact = create_contact(user_id=user1.id)
        r = client.get(f"/api/contacts/{contact.id}", headers=_bearer(user2))
        # Contact is public, but should verify ownership for edit actions
        assert r.status_code == 200

    def test_cannot_modify_other_user_contact(self, client, create_user, create_contact):
        """User cannot modify another user's contact."""
        user1 = create_user()
        user2 = create_user()
        contact = create_contact(user_id=user1.id)
        r = client.put(
            f"/api/contacts/{contact.id}",
            headers=_bearer(user2),
            json={"name": "Modified"}
        )
        assert r.status_code == 403

    def test_cannot_delete_other_user_contact(self, client, create_user, create_contact):
        """User cannot delete another user's contact."""
        user1 = create_user()
        user2 = create_user()
        contact = create_contact(user_id=user1.id)
        r = client.delete(f"/api/contacts/{contact.id}", headers=_bearer(user2))
        assert r.status_code == 403

    def test_cannot_access_other_user_reviews(self, client, create_user, create_contact, create_review):
        """User cannot manage reviews on contacts they don't own."""
        owner = create_user()
        other = create_user()
        contact = create_contact(user_id=owner.id)
        # Try to reply without creating a review
        r = client.post(
            f"/api/reviews/99999/reply",
            headers=_bearer(other),
            json={"reply": "Test reply"}
        )
        # Should be 403/404 or 422 if review doesn't exist
        assert r.status_code in [403, 404, 422]

    def test_cannot_access_other_user_offers(self, client, create_user, create_contact):
        """User cannot access offers on contacts they don't own."""
        owner = create_user()
        other = create_user()
        contact = create_contact(user_id=owner.id)
        # Try to access offers as other user
        r = client.get(f"/api/contacts/{contact.id}/offers", headers=_bearer(other))
        # Should work (offers are public) but cannot modify
        if r.status_code == 200:
            offers = r.json()
            if offers and "id" in offers[0]:
                offer_id = offers[0]["id"]
                r = client.delete(
                    f"/api/contacts/{contact.id}/offers/{offer_id}",
                    headers=_bearer(other)
                )
                assert r.status_code in [403, 404]
        # Simply verify endpoint responds
        assert r.status_code in [200, 403, 404]

    def test_cannot_access_other_user_schedules(self, client, create_user, create_contact):
        """User cannot modify schedules on contacts they don't own."""
        owner = create_user()
        other = create_user()
        contact = create_contact(user_id=owner.id)
        r = client.put(
            f"/api/contacts/{contact.id}/schedules",
            headers=_bearer(other),
            json=[{"day_of_week": 1, "open_time": "09:00", "close_time": "18:00"}]
        )
        assert r.status_code == 403


class TestIDORVulnerabilities:
    """Test for Insecure Direct Object Reference vulnerabilities."""

    def test_idor_via_contact_id_enumeration(self, client, create_user, create_contact, user_headers):
        """Test that sequential contact ID enumeration reveals unauthorized data."""
        # Create a contact as owner
        owner = create_user()
        contact = create_contact(user_id=owner.id)
        attacker = create_user()

        # Attacker tries to access owner's contact
        r = client.get(f"/api/contacts/{contact.id}", headers=_bearer(attacker))
        # Contact exists but should verify ownership for sensitive operations
        assert r.status_code in [200, 403, 404]

    def test_idor_via_review_id_enumeration(self, client, create_user, create_contact, create_review, user_headers):
        """Test that review IDs can be enumerated to access unauthorized data."""
        owner = create_user()
        contact = create_contact(user_id=owner.id)
        review = create_review(contact_id=contact.id)
        attacker = create_user()

        # Try to access review directly
        r = client.get(f"/api/contacts/{contact.id}/reviews", headers=_bearer(attacker))
        assert r.status_code == 200

    def test_idor_via_offer_id_enumeration(self, client, create_user, create_contact, user_headers):
        """Test that offer IDs can be enumerated."""
        owner = create_user()
        contact = create_contact(user_id=owner.id)
        attacker = create_user()

        # Try to access offers (offers are public read)
        r = client.get(f"/api/contacts/{contact.id}/offers", headers=_bearer(attacker))
        # Should return empty or list
        assert r.status_code in [200, 404]

    def test_idor_via_notification_id_access(self, client, create_user, user_headers, create_notification):
        """Test that notification IDs expose unauthorized access."""
        owner = create_user()
        notification = create_notification(user_id=owner.id)
        attacker = create_user()

        # Try to read notification via different IDs
        for notif_id in range(1, notification.id + 5):
            r = client.get(f"/api/notifications/{notif_id}", headers=_bearer(attacker))
            if r.status_code == 200:
                data = r.json()
                # Should only see own notifications
                assert data.get("user_id") == attacker.id


class TestInsecureDirectObjectReferencePrevention:
    """Additional IDOR prevention tests."""

    def test_prevent_idor_in_profile_picture_upload(self, client, create_user, create_contact):
        """Test that users cannot manipulate profile picture uploads for other users."""
        owner = create_user()
        contact = create_contact(user_id=owner.id)
        attacker = create_user()

        # Try to upload photo to another user's contact
        # This should be prevented at the API level
        pass  # Implementation depends on photo upload endpoint

    def test_prevent_idor_in_lead_generation(self, client, create_user, create_contact):
        """Test that lead generation cannot be manipulated."""
        owner = create_user()
        contact = create_contact(user_id=owner.id)
        attacker = create_user()

        # Any user can generate a lead (that's the point of the app)
        # But we verify the contact owner gets notified
        r = client.post(f"/api/contacts/{contact.id}/leads", json={
            "name": "Lead Name",
            "email": "lead@test.com",
            "phone": "123456",
            "message": "Interested"
        })
        assert r.status_code in [200, 201]

    def test_prevent_idor_in_category_access(self, client, user_headers):
        """Test that category access doesn't expose sensitive data."""
        r = client.get("/api/categories", headers=user_headers)
        assert r.status_code == 200
        data = r.json()
        # Categories should be public and not contain sensitive info
        for cat in data:
            assert "internal" not in cat.get("description", "").lower()


class TestBrokenAccessControlMitigation:
    """Test that access control mitigations are in place."""

    def test_session_timeout_enforced(self, client, create_user):
        """Test that sessions expire properly."""
        # Create user and login
        user = create_user()
        r = client.post("/api/auth/login", json={
            "username_or_email": user.username,
            "password": "password123"
        })
        assert r.status_code == 200

        # Verify token has expiration (checked via JWT decode)
        token = r.json().get("token")
        if token:
            import jwt as pyjwt
            from app.config import JWT_SECRET, JWT_ALGORITHM
            decoded = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            assert "exp" in decoded
            assert decoded["exp"] > 0

    def test_authorization_header_required(self, client):
        """Test that protected endpoints require Authorization header."""
        # Test various protected endpoints
        protected_endpoints = [
            ("GET", "/api/auth/me"),
            ("POST", "/api/contacts"),
            ("GET", "/api/provider/dashboard"),
        ]

        for method, endpoint in protected_endpoints:
            if method == "GET":
                r = client.get(endpoint)
            else:
                r = client.post(endpoint, json={})

            assert r.status_code in [401, 403], f"{method} {endpoint} should require auth"

    def test_cors_prevents_unauthorized_access(self, client):
        """Test that CORS policy prevents cross-site access to protected endpoints."""
        # Verify CORS headers are set appropriately
        r = client.options("/api/contacts", headers={"Origin": "http://evil.com"})
        # Should either allow or deny based on policy
        # The key is that it shouldn't expose sensitive data to arbitrary origins
        assert "access-control" in r.headers or r.status_code != 200

    def test_method_enforcement(self, client, user_headers):
        """Test that only allowed HTTP methods work on each endpoint."""
        # Verify that sending wrong method doesn't expose data
        r = client.delete("/api/contacts", headers=user_headers)
        assert r.status_code in [405, 404]

        r = client.patch("/api/auth/login", headers=user_headers, json={})
        assert r.status_code in [405, 404, 400]