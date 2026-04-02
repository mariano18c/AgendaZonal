"""Deep tests for reviews.py uncovered paths: photo upload, reject (was_approved), verification level."""
import pytest
import io
from PIL import Image
from app.models.contact import Contact
from app.models.review import Review


def _make_jpeg(width=100, height=100):
    img = Image.new("RGB", (width, height), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def _login(client, username, password="password123"):
    resp = client.post("/api/auth/login", json={
        "username_or_email": username,
        "password": password,
    })
    return {"Authorization": f"Bearer {resp.json()['token']}"}


# ===========================================================================
# REVIEW PHOTO UPLOAD: POST /api/reviews/{id}/photo
# ===========================================================================

class TestUploadReviewPhoto:
    """POST /api/reviews/{id}/photo"""

    def test_upload_review_photo_success(self, client, create_user, database_session):
        reviewer = create_user(username="reviewer", email="reviewer@test.com")
        owner = create_user(username="owner", email="owner@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        review = Review(contact_id=contact.id, user_id=reviewer.id, rating=5, comment="Great!")
        database_session.add(review)
        database_session.commit()
        database_session.refresh(review)

        headers = _login(client, "reviewer")
        jpeg = _make_jpeg()

        resp = client.post(
            f"/api/reviews/{review.id}/photo",
            headers=headers,
            files={"file": ("review.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 200
        assert resp.json()["photo_path"] is not None

    def test_upload_review_photo_not_author(self, client, create_user, database_session):
        reviewer = create_user(username="reviewer", email="reviewer@test.com")
        stranger = create_user(username="stranger", email="stranger@test.com")
        owner = create_user(username="owner", email="owner@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        review = Review(contact_id=contact.id, user_id=reviewer.id, rating=5, comment="Great!")
        database_session.add(review)
        database_session.commit()
        database_session.refresh(review)

        headers = _login(client, "stranger")
        jpeg = _make_jpeg()

        resp = client.post(
            f"/api/reviews/{review.id}/photo",
            headers=headers,
            files={"file": ("review.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 403

    def test_upload_review_photo_nonexistent_review(self, client, auth_headers):
        headers = auth_headers()
        jpeg = _make_jpeg()
        resp = client.post(
            "/api/reviews/99999/photo",
            headers=headers,
            files={"file": ("review.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 404

    def test_upload_review_photo_not_jpg(self, client, create_user, database_session):
        reviewer = create_user(username="reviewer", email="reviewer@test.com")
        owner = create_user(username="owner", email="owner@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        review = Review(contact_id=contact.id, user_id=reviewer.id, rating=5, comment="OK")
        database_session.add(review)
        database_session.commit()
        database_session.refresh(review)

        headers = _login(client, "reviewer")
        png = io.BytesIO()
        Image.new("RGB", (100, 100)).save(png, format="PNG")
        png.seek(0)

        resp = client.post(
            f"/api/reviews/{review.id}/photo",
            headers=headers,
            files={"file": ("review.png", png, "image/png")},
        )
        assert resp.status_code == 400

    def test_upload_review_photo_too_large(self, client, create_user, database_session):
        reviewer = create_user(username="reviewer", email="reviewer@test.com")
        owner = create_user(username="owner", email="owner@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        review = Review(contact_id=contact.id, user_id=reviewer.id, rating=5, comment="OK")
        database_session.add(review)
        database_session.commit()
        database_session.refresh(review)

        headers = _login(client, "reviewer")
        # Create payload > 2MB with JPEG magic header
        big = io.BytesIO(b'\xFF\xD8\xFF\xE0' + b'\x00' * (2 * 1024 * 1024 + 1))

        resp = client.post(
            f"/api/reviews/{review.id}/photo",
            headers=headers,
            files={"file": ("big.jpg", big, "image/jpeg")},
        )
        assert resp.status_code == 400

    def test_upload_review_photo_invalid_magic(self, client, create_user, database_session):
        reviewer = create_user(username="reviewer", email="reviewer@test.com")
        owner = create_user(username="owner", email="owner@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        review = Review(contact_id=contact.id, user_id=reviewer.id, rating=5, comment="OK")
        database_session.add(review)
        database_session.commit()
        database_session.refresh(review)

        headers = _login(client, "reviewer")
        fake = io.BytesIO(b"NOT_JPEG")

        resp = client.post(
            f"/api/reviews/{review.id}/photo",
            headers=headers,
            files={"file": ("fake.jpg", fake, "image/jpeg")},
        )
        assert resp.status_code == 400


# ===========================================================================
# REJECT REVIEW — was_approved path (recalculate_rating)
# ===========================================================================

class TestRejectReviewWasApproved:
    """POST /api/admin/reviews/{id}/reject — recalculates if was approved"""

    def test_reject_approved_review_recalculates(self, client, moderator_user, create_user, database_session):
        """Rejecting an already-approved review should recalculate the contact rating."""
        _, mod_headers = moderator_user
        owner = create_user(username="owner", email="owner@test.com")
        reviewer = create_user(username="reviewer", email="reviewer@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        # Create and approve a review
        review = Review(contact_id=contact.id, user_id=reviewer.id, rating=5, comment="Great!")
        database_session.add(review)
        database_session.commit()
        database_session.refresh(review)

        # Approve it
        client.post(f"/api/admin/reviews/{review.id}/approve", headers=mod_headers)

        # Verify rating was set
        database_session.refresh(contact)
        assert contact.review_count == 1
        assert contact.avg_rating == 5.0

        # Now reject it
        resp = client.post(f"/api/admin/reviews/{review.id}/reject", headers=mod_headers)
        assert resp.status_code == 200
        assert resp.json()["is_approved"] is False

        # Rating should be recalculated to 0
        database_session.refresh(contact)
        assert contact.review_count == 0
        assert contact.avg_rating == 0

    def test_reject_unapproved_review_no_recalc(self, client, moderator_user, create_user, database_session):
        """Rejecting a never-approved review should NOT recalculate."""
        _, mod_headers = moderator_user
        owner = create_user(username="owner", email="owner@test.com")
        reviewer = create_user(username="reviewer", email="reviewer@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        review = Review(contact_id=contact.id, user_id=reviewer.id, rating=3, comment="OK")
        database_session.add(review)
        database_session.commit()
        database_session.refresh(review)

        resp = client.post(f"/api/admin/reviews/{review.id}/reject", headers=mod_headers)
        assert resp.status_code == 200
        assert resp.json()["is_approved"] is False

    def test_reject_review_not_found(self, client, moderator_user):
        _, mod_headers = moderator_user
        resp = client.post("/api/admin/reviews/99999/reject", headers=mod_headers)
        assert resp.status_code == 404

    def test_reject_review_non_mod_rejected(self, client, auth_headers, create_user, database_session):
        owner = create_user(username="owner", email="owner@test.com")
        reviewer = create_user(username="reviewer", email="reviewer@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        review = Review(contact_id=contact.id, user_id=reviewer.id, rating=5, comment="Good")
        database_session.add(review)
        database_session.commit()
        database_session.refresh(review)

        headers = auth_headers(username="regular", email="regular@test.com")
        resp = client.post(f"/api/admin/reviews/{review.id}/reject", headers=headers)
        assert resp.status_code == 403


# ===========================================================================
# VERIFICATION LEVEL — level 0 path
# ===========================================================================

class TestVerificationLevelZero:
    """PUT /api/admin/contacts/{id}/verification — setting to 0"""

    def test_set_verification_level_to_zero(self, client, moderator_user, create_user, database_session):
        """Setting verification_level to 0 should clear verified_by and verified_at."""
        _, mod_headers = moderator_user
        owner = create_user(username="owner", email="owner@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id, verification_level=2)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.put(
            f"/api/admin/contacts/{contact.id}/verification",
            headers=mod_headers,
            json={"verification_level": 0},
        )
        assert resp.status_code == 200
        assert resp.json()["verification_level"] == 0
        assert resp.json()["is_verified"] is False

    def test_set_verification_level_nonexistent(self, client, moderator_user):
        _, mod_headers = moderator_user
        resp = client.put(
            "/api/admin/contacts/99999/verification",
            headers=mod_headers,
            json={"verification_level": 1},
        )
        assert resp.status_code == 404

    def test_set_verification_level_non_mod_rejected(self, client, auth_headers, create_user, database_session):
        owner = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = auth_headers(username="regular", email="regular@test.com")
        resp = client.put(
            f"/api/admin/contacts/{contact.id}/verification",
            headers=headers,
            json={"verification_level": 1},
        )
        assert resp.status_code == 403


# ===========================================================================
# APPROVE REVIEW — already approved path
# ===========================================================================

class TestApproveReviewEdgeCases:
    """POST /api/admin/reviews/{id}/approve"""

    def test_approve_already_approved_review(self, client, moderator_user, create_user, database_session):
        _, mod_headers = moderator_user
        owner = create_user(username="owner", email="owner@test.com")
        reviewer = create_user(username="reviewer", email="reviewer@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        review = Review(contact_id=contact.id, user_id=reviewer.id, rating=5, comment="Good",
                        is_approved=True)
        database_session.add(review)
        database_session.commit()
        database_session.refresh(review)

        resp = client.post(f"/api/admin/reviews/{review.id}/approve", headers=mod_headers)
        assert resp.status_code == 400

    def test_approve_review_not_found(self, client, moderator_user):
        _, mod_headers = moderator_user
        resp = client.post("/api/admin/reviews/99999/approve", headers=mod_headers)
        assert resp.status_code == 404
