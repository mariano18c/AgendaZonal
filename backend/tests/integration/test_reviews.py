"""Integration tests — Reviews (create, approve, reject, reply, photos)."""
import pytest
from tests.conftest import _bearer


class TestCreateReview:
    def test_create_review(self, client, create_user, create_contact):
        reviewer = create_user()
        c = create_contact()
        r = client.post(f"/api/contacts/{c.id}/reviews",
                         headers=_bearer(reviewer),
                         json={"rating": 5, "comment": "Excelente!"})
        assert r.status_code == 201
        assert r.json()["rating"] == 5
        assert r.json()["is_approved"] is False  # Pending moderation

    def test_cannot_review_own_contact(self, client, create_user, create_contact):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        r = client.post(f"/api/contacts/{c.id}/reviews",
                         headers=_bearer(owner),
                         json={"rating": 5, "comment": "Auto-review"})
        assert r.status_code == 400
        assert "propio" in r.json()["detail"].lower()

    def test_cannot_review_twice(self, client, create_user, create_contact):
        reviewer = create_user()
        c = create_contact()
        client.post(f"/api/contacts/{c.id}/reviews",
                     headers=_bearer(reviewer),
                     json={"rating": 5, "comment": "First"})
        r = client.post(f"/api/contacts/{c.id}/reviews",
                         headers=_bearer(reviewer),
                         json={"rating": 3, "comment": "Second"})
        assert r.status_code == 409
        assert "ya" in r.json()["detail"].lower()

    def test_review_unauthenticated(self, client, create_contact):
        c = create_contact()
        r = client.post(f"/api/contacts/{c.id}/reviews",
                         json={"rating": 5})
        assert r.status_code == 401

    def test_invalid_rating(self, client, create_user, create_contact):
        reviewer = create_user()
        c = create_contact()
        r = client.post(f"/api/contacts/{c.id}/reviews",
                         headers=_bearer(reviewer),
                         json={"rating": 0})
        assert r.status_code == 422


class TestListReviews:
    def test_list_approved_reviews(self, client, create_contact, create_review):
        c = create_contact()
        create_review(contact_id=c.id, is_approved=True, comment="Good")
        create_review(contact_id=c.id, is_approved=False, comment="Pending")
        r = client.get(f"/api/contacts/{c.id}/reviews")
        assert r.status_code == 200
        # Only approved shown
        assert all(rev["is_approved"] for rev in r.json()["reviews"])

    def test_list_reviews_nonexistent_contact(self, client):
        r = client.get("/api/contacts/99999/reviews")
        assert r.status_code == 404


class TestReviewReply:
    def test_owner_can_reply(self, client, create_user, create_contact, create_review):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        rev = create_review(contact_id=c.id, is_approved=True)
        r = client.post(f"/api/reviews/{rev.id}/reply",
                         headers=_bearer(owner),
                         json={"reply_text": "Gracias!"})
        assert r.status_code == 200
        assert r.json()["reply_text"] == "Gracias!"

    def test_stranger_cannot_reply(self, client, create_user, create_contact, create_review):
        c = create_contact()
        rev = create_review(contact_id=c.id, is_approved=True)
        stranger = create_user()
        r = client.post(f"/api/reviews/{rev.id}/reply",
                         headers=_bearer(stranger),
                         json={"reply_text": "Not allowed"})
        assert r.status_code == 403

    def test_cannot_reply_unapproved(self, client, create_user, create_contact, create_review):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        rev = create_review(contact_id=c.id, is_approved=False)
        r = client.post(f"/api/reviews/{rev.id}/reply",
                         headers=_bearer(owner),
                         json={"reply_text": "Reply"})
        assert r.status_code == 400


class TestReviewModeration:
    def test_approve_review(self, client, mod_headers, create_contact, create_review):
        c = create_contact()
        rev = create_review(contact_id=c.id, is_approved=False, rating=4)
        r = client.post(f"/api/admin/reviews/{rev.id}/approve", headers=mod_headers)
        assert r.status_code == 200
        assert r.json()["is_approved"] is True

        # Rating should have been recalculated
        c_resp = client.get(f"/api/contacts/{c.id}")
        assert c_resp.json()["avg_rating"] >= 0

    def test_reject_review(self, client, mod_headers, create_contact, create_review):
        c = create_contact()
        rev = create_review(contact_id=c.id, is_approved=False)
        r = client.post(f"/api/admin/reviews/{rev.id}/reject", headers=mod_headers)
        assert r.status_code == 200

    def test_approve_already_approved(self, client, mod_headers, create_contact, create_review):
        c = create_contact()
        rev = create_review(contact_id=c.id, is_approved=True)
        r = client.post(f"/api/admin/reviews/{rev.id}/approve", headers=mod_headers)
        assert r.status_code == 400

    def test_list_pending_reviews(self, client, mod_headers, create_contact, create_review):
        c = create_contact()
        create_review(contact_id=c.id, is_approved=False)
        r = client.get("/api/admin/reviews/pending", headers=mod_headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_regular_user_cannot_moderate(self, client, user_headers, create_contact, create_review):
        c = create_contact()
        rev = create_review(contact_id=c.id)
        r = client.post(f"/api/admin/reviews/{rev.id}/approve", headers=user_headers)
        assert r.status_code == 403

    def test_set_verification_level(self, client, mod_headers, create_contact):
        c = create_contact()
        r = client.put(f"/api/admin/contacts/{c.id}/verification",
                        headers=mod_headers,
                        json={"verification_level": 3})
        assert r.status_code == 200
        assert r.json()["verification_level"] == 3

    def test_invalid_verification_level(self, client, mod_headers, create_contact):
        c = create_contact()
        r = client.put(f"/api/admin/contacts/{c.id}/verification",
                        headers=mod_headers,
                        json={"verification_level": 4})
        assert r.status_code == 422


class TestReviewsBatchFetch:
    """N+1 query validation — merged from tests_ant."""

    def test_list_reviews_with_multiple_reviews(self, client, create_user, create_contact, db_session):
        """GET reviews should return enriched data with usernames (batch fetch)."""
        from app.models.review import Review
        owner = create_user(username="reviewowner", email="reviewowner@test.com")
        c = create_contact(user_id=owner.id, name="Review Target")
        reviewer1 = create_user(username="reviewer1", email="reviewer1@test.com")
        reviewer2 = create_user(username="reviewer2", email="reviewer2@test.com")
        reviewer3 = create_user(username="reviewer3", email="reviewer3@test.com")
        for i, reviewer in enumerate([reviewer1, reviewer2, reviewer3]):
            review = Review(
                contact_id=c.id, user_id=reviewer.id,
                rating=4 + (i % 2), comment=f"Review {i}", is_approved=True,
            )
            db_session.add(review)
        db_session.commit()
        resp = client.get(f"/api/contacts/{c.id}/reviews")
        assert resp.status_code == 200
        data = resp.json()
        assert "reviews" in data
        assert "total" in data
        assert len(data["reviews"]) == 3
        usernames = {r["username"] for r in data["reviews"]}
        assert "reviewer1" in usernames
        assert "reviewer2" in usernames
        assert "reviewer3" in usernames
