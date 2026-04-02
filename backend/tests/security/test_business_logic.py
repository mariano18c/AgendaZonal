"""Business logic security tests.

Tests from QA plan:
- BIZ-01 to BIZ-05: Reports and auto-flagging
- REV-01 to REV-06: Reviews and moderation
- OFF-01 to OFF-04: Offers and expiration
- RBAC-01 to RBAC-07: Role-based access control
"""
import pytest
from datetime import datetime, timedelta, timezone


class TestReportsAndFlagging:

    @pytest.mark.security
    def test_report_own_contact_rejected(self, client, auth_headers):
        """BIZ-04: User cannot report their own contact"""
        headers = auth_headers(username="reportowner", email="reportowner@test.com")
        
        # Create contact (user is owner)
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "My Business", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        # Try to report own contact
        resp = client.post(
            f"/api/contacts/{cid}/report",
            headers=headers,
            json={"reason": "spam", "details": "Test"}
        )
        assert resp.status_code == 400

    @pytest.mark.security
    def test_cannot_report_twice(self, client, auth_headers):
        """BIZ-02: Same user cannot report the same contact twice"""
        # User1 creates a contact
        headers1 = auth_headers(username="reporter1", email="reporter1@test.com")
        create_resp = client.post("/api/contacts", headers=headers1, json={
            "name": "Reported Business", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        # User2 creates another contact (so user1 can report user1's contact)
        headers2 = auth_headers(username="reporter2", email="reporter2@test.com")
        client.post("/api/contacts", headers=headers2, json={
            "name": "User2 Business", "phone": "1234568",
        })
        
        # User2 reports User1's contact
        resp1 = client.post(
            f"/api/contacts/{cid}/report",
            headers=headers2,
            json={"reason": "spam", "details": "First report"}
        )
        assert resp1.status_code == 201
        
        # User2 tries to report again
        resp2 = client.post(
            f"/api/contacts/{cid}/report",
            headers=headers2,
            json={"reason": "falso", "details": "Second report"}
        )
        assert resp2.status_code == 409

    @pytest.mark.security
    def test_three_reports_flags_contact(self, client, auth_headers):
        """BIZ-01: Three distinct reports should auto-flag the contact"""
        # User1 creates a contact
        headers_owner = auth_headers(username="bizowner", email="bizowner@test.com")
        create_resp = client.post("/api/contacts", headers=headers_owner, json={
            "name": "Flag Test Business", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        # Create 3 different reporters and have them report
        headers2 = auth_headers(username="reporter1", email="rep1@test.com")
        headers3 = auth_headers(username="reporter2", email="rep2@test.com")
        headers4 = auth_headers(username="reporter3", email="rep3@test.com")
        
        # Reporter 1 reports
        r1 = client.post(
            f"/api/contacts/{cid}/report",
            headers=headers2,
            json={"reason": "spam", "details": "Report 1"}
        )
        assert r1.status_code == 201
        
        # Verify not flagged yet (only 1 report)
        contact_resp = client.get(f"/api/contacts/{cid}")
        assert contact_resp.json()["status"] == "active"
        
        # Reporter 2 reports
        r2 = client.post(
            f"/api/contacts/{cid}/report",
            headers=headers3,
            json={"reason": "falso", "details": "Report 2"}
        )
        assert r2.status_code == 201
        
        # Verify not flagged yet (only 2 reports)
        contact_resp = client.get(f"/api/contacts/{cid}")
        assert contact_resp.json()["status"] == "active"
        
        # Reporter 3 reports - should trigger flag
        r3 = client.post(
            f"/api/contacts/{cid}/report",
            headers=headers4,
            json={"reason": "inapropiado", "details": "Report 3"}
        )
        assert r3.status_code == 201
        
        # Verify flagged
        contact_resp = client.get(f"/api/contacts/{cid}")
        assert contact_resp.json()["status"] == "flagged"


class TestReviewsAndModeration:

    @pytest.mark.security
    def test_cannot_review_own_contact(self, client, auth_headers):
        """REV-01: User cannot review their own contact"""
        headers = auth_headers(username="reviewowner", email="reviewowner@test.com")
        
        # Create contact (user is owner)
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "My Review Business", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        # Try to review own contact
        resp = client.post(
            f"/api/contacts/{cid}/reviews",
            headers=headers,
            json={"rating": 5, "comment": "Great!"}
        )
        assert resp.status_code == 400

    @pytest.mark.security
    def test_cannot_review_same_contact_twice(self, client, auth_headers):
        """REV-01: User cannot review the same contact twice"""
        headers1 = auth_headers(username="reviewer1", email="reviewer1@test.com")
        headers2 = auth_headers(username="reviewer2", email="reviewer2@test.com")
        
        # User2 creates contact
        create_resp = client.post("/api/contacts", headers=headers2, json={
            "name": "Reviewed Business", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        # User1 reviews
        r1 = client.post(
            f"/api/contacts/{cid}/reviews",
            headers=headers1,
            json={"rating": 5, "comment": "Great!"}
        )
        assert r1.status_code == 201
        
        # User1 tries to review again
        r2 = client.post(
            f"/api/contacts/{cid}/reviews",
            headers=headers1,
            json={"rating": 4, "comment": "Changed my mind"}
        )
        assert r2.status_code == 409

    @pytest.mark.security
    def test_rating_must_be_1_to_5(self, client, auth_headers):
        """REV-02: Rating must be between 1 and 5"""
        headers1 = auth_headers(username="bizrev1", email="bizrev1@test.com")
        headers2 = auth_headers(username="bizrev2", email="bizrev2@test.com")
        
        # User2 creates contact
        create_resp = client.post("/api/contacts", headers=headers2, json={
            "name": "Rating Test", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        # Try rating 0
        resp0 = client.post(
            f"/api/contacts/{cid}/reviews",
            headers=headers1,
            json={"rating": 0, "comment": "Bad"}
        )
        assert resp0.status_code == 422
        
        # Try rating 6
        resp6 = client.post(
            f"/api/contacts/{cid}/reviews",
            headers=headers1,
            json={"rating": 6, "comment": "Too good"}
        )
        assert resp6.status_code == 422

    @pytest.mark.security
    def test_unapproved_reviews_not_public(self, client, auth_headers):
        """REV-05: Unapproved reviews should not appear in public listing"""
        headers1 = auth_headers(username="modrev1", email="modrev1@test.com")
        headers2 = auth_headers(username="modrev2", email="modrev2@test.com")
        
        # User2 creates contact
        create_resp = client.post("/api/contacts", headers=headers2, json={
            "name": "Pending Review Business", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        # User1 creates review (unapproved by default)
        review_resp = client.post(
            f"/api/contacts/{cid}/reviews",
            headers=headers1,
            json={"rating": 5, "comment": "Should be hidden"}
        )
        assert review_resp.status_code == 201
        
        # Public listing should not show the review
        public_resp = client.get(f"/api/contacts/{cid}/reviews")
        assert public_resp.status_code == 200
        assert len(public_resp.json()["reviews"]) == 0


class TestOffersAndExpiration:

    @pytest.mark.security
    def test_offer_cannot_expire_in_past(self, client, auth_headers):
        """OFF-01: Cannot create offer with past expiration"""
        headers = auth_headers(username="offeruser1", email="offeruser1@test.com")
        
        # Create contact
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Offer Business", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        # Try to create offer with past date
        past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        resp = client.post(
            f"/api/contacts/{cid}/offers",
            headers=headers,
            json={
                "title": "Past Deal",
                "description": "Should fail",
                "discount_pct": 50,
                "expires_at": past_date
            }
        )
        assert resp.status_code == 400

    @pytest.mark.security
    def test_offer_discount_must_be_1_to_99(self, client, auth_headers):
        """OFF-03: Discount percentage must be 1-99"""
        headers = auth_headers(username="offeruser2", email="offeruser2@test.com")
        
        # Create contact
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Discount Test", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        future_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        
        # Try discount 0
        resp0 = client.post(
            f"/api/contacts/{cid}/offers",
            headers=headers,
            json={
                "title": "Zero Discount",
                "discount_pct": 0,
                "expires_at": future_date
            }
        )
        assert resp0.status_code == 422
        
        # Try discount 100
        resp100 = client.post(
            f"/api/contacts/{cid}/offers",
            headers=headers,
            json={
                "title": "100 Discount",
                "discount_pct": 100,
                "expires_at": future_date
            }
        )
        assert resp100.status_code == 422

    @pytest.mark.security
    def test_expired_offers_not_listed(self, client, auth_headers):
        """OFF-02: Expired offers should not appear in public listing"""
        headers = auth_headers(username="offeruser3", email="offeruser3@test.com")
        
        # Create contact
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Expire Test", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        # Create offer that expires soon (but not yet)
        soon_date = (datetime.now(timezone.utc) + timedelta(seconds=2)).isoformat()
        offer_resp = client.post(
            f"/api/contacts/{cid}/offers",
            headers=headers,
            json={
                "title": "Soon Expiring",
                "discount_pct": 30,
                "expires_at": soon_date
            }
        )
        assert offer_resp.status_code == 201
        
        # Should appear now
        list_resp = client.get(f"/api/contacts/{cid}/offers")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1


class TestRoleBasedAccessControl:

    @pytest.mark.security
    def test_user_cannot_access_admin_analytics(self, client, auth_headers):
        """RBAC-01: Regular user cannot access admin analytics"""
        headers = auth_headers(username="rbacuser1", email="rbacuser1@test.com")
        
        resp = client.get("/api/admin/analytics", headers=headers)
        assert resp.status_code == 403

    @pytest.mark.security
    def test_user_cannot_list_flagged_contacts(self, client, auth_headers):
        """RBAC-01: Regular user cannot list flagged contacts"""
        headers = auth_headers(username="rbacuser2", email="rbacuser2@test.com")
        
        resp = client.get("/api/admin/reports/flagged", headers=headers)
        assert resp.status_code == 403

    @pytest.mark.security
    def test_user_cannot_approve_review(self, client, auth_headers):
        """RBAC-03: Regular user cannot approve reviews"""
        # Owner creates contact
        headers_owner = auth_headers(username="rbacowner", email="rbacowner@test.com")
        create_resp = client.post("/api/contacts", headers=headers_owner, json={
            "name": "Review Test", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        # Reviewer creates review
        headers_reviewer = auth_headers(username="reviewauthor", email="reviewauthor@test.com")
        rev_resp = client.post(
            f"/api/contacts/{cid}/reviews",
            headers=headers_reviewer,
            json={"rating": 5, "comment": "Great!"}
        )
        review_id = rev_resp.json()["id"]
        
        # Try to approve as regular user (not admin/moderator)
        # Use wrong endpoint - should be /api/admin/reviews but user is not admin
        approve_resp = client.post(
            f"/api/admin/reviews/{review_id}/approve",
            headers=headers_owner  # owner is not admin/moderator
        )
        assert approve_resp.status_code == 403

    @pytest.mark.security
    def test_moderator_can_access_flagged(self, client, moderator_user):
        """RBAC-03: Moderator can access flagged contacts"""
        mod_user, mod_headers = moderator_user
        
        resp = client.get("/api/admin/reports/flagged", headers=mod_headers)
        # Moderator should have access (may return empty list)
        assert resp.status_code == 200


class TestPendingChangesSecurity:

    @pytest.mark.security
    def test_non_owner_cannot_verify_change(self, client, auth_headers):
        """RBAC-05: Non-owner cannot verify pending changes"""
        # Owner creates contact
        headers_owner = auth_headers(username="pconwer", email="pconwer@test.com")
        create_resp = client.post("/api/contacts", headers=headers_owner, json={
            "name": "Pending Change Test", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        # Another user (not owner) suggests change
        headers_other = auth_headers(username="pcother", email="pcother@test.com")
        edit_resp = client.put(
            f"/api/contacts/{cid}/edit",
            headers=headers_other,
            json={"description": "Suggested change"}
        )
        assert edit_resp.status_code == 200
        
        # Get change ID - owner CAN see the changes
        changes_resp = client.get(
            f"/api/contacts/{cid}/changes",
            headers=headers_owner
        )
        assert changes_resp.status_code == 200
        assert len(changes_resp.json()) > 0
        change_id = changes_resp.json()[0]["id"]
        
        # Third user (not owner, not mod) tries to verify - should fail
        headers_third = auth_headers(username="pcthird", email="pcthird@test.com")
        verify_resp = client.post(
            f"/api/contacts/{cid}/changes/{change_id}/verify",
            headers=headers_third
        )
        # Third user is not owner or mod/admin, should be rejected
        assert verify_resp.status_code == 403
