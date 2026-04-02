"""Integration tests for reviews system and verification levels."""
import pytest


class TestReviews:
    """Test review CRUD and moderation flow."""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_headers, contact_factory, moderator_user):
        """Create contacts and users for review testing."""
        self.owner_headers = auth_headers(username="rev_owner", email="revowner@test.com")
        self.reviewer_headers = auth_headers(username="rev_reviewer", email="revreviewer@test.com")
        self.mod_user, self.mod_headers = moderator_user

        self.contact_id = contact_factory(
            self.owner_headers, name="Test Contact", phone="3411111111",
            category_id=1,
        )

    def test_create_review(self, client):
        """User can create a review for a contact."""
        resp = client.post(f"/api/contacts/{self.contact_id}/reviews",
            headers=self.reviewer_headers,
            json={"rating": 5, "comment": "Excelente servicio!"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["rating"] == 5
        assert data["comment"] == "Excelente servicio!"
        assert data["is_approved"] is False
        assert data["username"] == "rev_reviewer"

    def test_create_review_without_auth(self, client):
        """Anonymous user cannot create a review."""
        # Clear cookies to ensure no auth is sent
        client.cookies.clear()
        resp = client.post(f"/api/contacts/{self.contact_id}/reviews",
            json={"rating": 5},
        )
        assert resp.status_code == 401

    def test_duplicate_review(self, client):
        """Same user cannot review same contact twice."""
        client.post(f"/api/contacts/{self.contact_id}/reviews",
            headers=self.reviewer_headers,
            json={"rating": 5},
        )
        resp = client.post(f"/api/contacts/{self.contact_id}/reviews",
            headers=self.reviewer_headers,
            json={"rating": 3},
        )
        assert resp.status_code == 409

    def test_self_review_blocked(self, client):
        """Owner cannot review their own contact."""
        resp = client.post(f"/api/contacts/{self.contact_id}/reviews",
            headers=self.owner_headers,
            json={"rating": 5},
        )
        assert resp.status_code == 400

    def test_invalid_rating_low(self, client):
        """Rating must be >= 1."""
        resp = client.post(f"/api/contacts/{self.contact_id}/reviews",
            headers=self.reviewer_headers,
            json={"rating": 0},
        )
        assert resp.status_code == 422

    def test_invalid_rating_high(self, client):
        """Rating must be <= 5."""
        resp = client.post(f"/api/contacts/{self.contact_id}/reviews",
            headers=self.reviewer_headers,
            json={"rating": 6},
        )
        assert resp.status_code == 422

    def test_list_reviews_empty(self, client):
        """No approved reviews returns empty list."""
        resp = client.get(f"/api/contacts/{self.contact_id}/reviews")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["reviews"] == []

    def test_pending_review_not_public(self, client):
        """Pending reviews are not shown in public listing."""
        client.post(f"/api/contacts/{self.contact_id}/reviews",
            headers=self.reviewer_headers,
            json={"rating": 5, "comment": "Pendiente"},
        )
        resp = client.get(f"/api/contacts/{self.contact_id}/reviews")
        assert resp.json()["total"] == 0

    def test_approve_review(self, client):
        """Moderator can approve a review, then it appears publicly."""
        create_resp = client.post(f"/api/contacts/{self.contact_id}/reviews",
            headers=self.reviewer_headers,
            json={"rating": 4, "comment": "Muy bueno"},
        )
        review_id = create_resp.json()["id"]

        approve_resp = client.post(f"/api/admin/reviews/{review_id}/approve",
            headers=self.mod_headers,
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["is_approved"] is True

        list_resp = client.get(f"/api/contacts/{self.contact_id}/reviews")
        assert list_resp.json()["total"] == 1
        assert list_resp.json()["reviews"][0]["comment"] == "Muy bueno"

    def test_approve_updates_rating(self, client, auth_headers):
        """Approving reviews updates contact avg_rating."""
        r1 = client.post(f"/api/contacts/{self.contact_id}/reviews",
            headers=self.reviewer_headers,
            json={"rating": 5},
        ).json()["id"]

        # Second reviewer via auth_headers fixture
        r2_headers = auth_headers(username="rev_r2", email="revr2@test.com")
        r2 = client.post(f"/api/contacts/{self.contact_id}/reviews",
            headers=r2_headers,
            json={"rating": 3},
        ).json()["id"]

        client.post(f"/api/admin/reviews/{r1}/approve", headers=self.mod_headers)
        client.post(f"/api/admin/reviews/{r2}/approve", headers=self.mod_headers)

        contact = client.get(f"/api/contacts/{self.contact_id}").json()
        assert contact["avg_rating"] == 4.0  # (5+3)/2
        assert contact["review_count"] == 2

    def test_reject_review(self, client):
        """Moderator can reject a review."""
        create_resp = client.post(f"/api/contacts/{self.contact_id}/reviews",
            headers=self.reviewer_headers,
            json={"rating": 1, "comment": "Malo"},
        )
        review_id = create_resp.json()["id"]

        resp = client.post(f"/api/admin/reviews/{review_id}/reject",
            headers=self.mod_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_approved"] is False

        list_resp = client.get(f"/api/contacts/{self.contact_id}/reviews")
        assert list_resp.json()["total"] == 0

    def test_reject_approved_recalculates(self, client):
        """Rejecting an already-approved review recalculates rating."""
        create_resp = client.post(f"/api/contacts/{self.contact_id}/reviews",
            headers=self.reviewer_headers,
            json={"rating": 5},
        )
        review_id = create_resp.json()["id"]

        client.post(f"/api/admin/reviews/{review_id}/approve", headers=self.mod_headers)
        contact = client.get(f"/api/contacts/{self.contact_id}").json()
        assert contact["avg_rating"] == 5.0

        client.post(f"/api/admin/reviews/{review_id}/reject", headers=self.mod_headers)
        contact = client.get(f"/api/contacts/{self.contact_id}").json()
        assert contact["avg_rating"] == 0
        assert contact["review_count"] == 0

    def test_non_mod_cannot_approve(self, client):
        """Regular user cannot approve reviews."""
        create_resp = client.post(f"/api/contacts/{self.contact_id}/reviews",
            headers=self.reviewer_headers,
            json={"rating": 5},
        )
        review_id = create_resp.json()["id"]

        resp = client.post(f"/api/admin/reviews/{review_id}/approve",
            headers=self.reviewer_headers,
        )
        assert resp.status_code == 403

    def test_pending_reviews_list(self, client):
        """Moderator sees pending reviews list."""
        client.post(f"/api/contacts/{self.contact_id}/reviews",
            headers=self.reviewer_headers,
            json={"rating": 4, "comment": "Pendiente 1"},
        )

        resp = client.get("/api/admin/reviews/pending", headers=self.mod_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert data["reviews"][0]["contact_name"] == "Test Contact"

    def test_non_mod_cannot_see_pending(self, client):
        """Regular user cannot access pending reviews."""
        resp = client.get("/api/admin/reviews/pending", headers=self.reviewer_headers)
        assert resp.status_code == 403


class TestVerificationLevels:
    """Test verification level system."""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_headers, contact_factory, moderator_user):
        self.owner_headers = auth_headers(username="v_owner2", email="vowner2@test.com")
        self.mod_user, self.mod_headers = moderator_user
        self.contact_id = contact_factory(
            self.owner_headers, name="Verify Contact", phone="3412222222",
            category_id=1,
        )

    def test_set_verification_level(self, client):
        """Moderator can set verification level."""
        resp = client.put(f"/api/admin/contacts/{self.contact_id}/verification",
            headers=self.mod_headers,
            json={"verification_level": 2},
        )
        assert resp.status_code == 200
        assert resp.json()["verification_level"] == 2
        assert resp.json()["is_verified"] is True

    def test_verification_zero_unverifies(self, client):
        """Setting level to 0 removes verification."""
        client.put(f"/api/admin/contacts/{self.contact_id}/verification",
            headers=self.mod_headers,
            json={"verification_level": 2},
        )
        resp = client.put(f"/api/admin/contacts/{self.contact_id}/verification",
            headers=self.mod_headers,
            json={"verification_level": 0},
        )
        assert resp.json()["verification_level"] == 0
        assert resp.json()["is_verified"] is False

    def test_non_mod_cannot_verify(self, client):
        """Regular user cannot change verification level."""
        resp = client.put(f"/api/admin/contacts/{self.contact_id}/verification",
            headers=self.owner_headers,
            json={"verification_level": 1},
        )
        assert resp.status_code == 403

    def test_invalid_level(self, client):
        """Invalid verification level returns 422."""
        resp = client.put(f"/api/admin/contacts/{self.contact_id}/verification",
            headers=self.mod_headers,
            json={"verification_level": 5},
        )
        assert resp.status_code == 422

    def test_level_in_contact_response(self, client):
        """Contact response includes verification_level."""
        client.put(f"/api/admin/contacts/{self.contact_id}/verification",
            headers=self.mod_headers,
            json={"verification_level": 3},
        )
        contact = client.get(f"/api/contacts/{self.contact_id}").json()
        assert contact["verification_level"] == 3
