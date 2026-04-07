"""Tests for photos, schedules, related businesses, transfer-ownership, and cancel-deletion - adapted."""
import pytest
import io
from PIL import Image
from app.models.contact import Contact, ContactHistory
from app.models.contact_photo import ContactPhoto
from app.models.schedule import Schedule
from app.models.category import Category
from app.auth import create_token


def _make_jpeg(width=100, height=100):
    """Create a minimal valid JPEG in memory."""
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


# ===========================================================================
# PHOTOS: GET /api/contacts/{id}/photos
# ===========================================================================

class TestListPhotos:
    """GET /api/contacts/{id}/photos"""

    def test_list_photos_empty(self, client, create_user, db_session):
        """List photos for contact with no photos."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        resp = client.get(f"/api/contacts/{contact.id}/photos")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_photos_with_data(self, client, create_user, db_session):
        """List photos for contact with photos."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        photo = ContactPhoto(contact_id=contact.id, photo_path="/uploads/images/test.jpg", caption="Test", sort_order=1)
        db_session.add(photo)
        db_session.commit()

        resp = client.get(f"/api/contacts/{contact.id}/photos")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["caption"] == "Test"

    def test_list_photos_nonexistent_contact(self, client):
        """List photos for non-existent contact returns 404."""
        resp = client.get("/api/contacts/99999/photos")
        assert resp.status_code == 404


# ===========================================================================
# PHOTOS: POST /api/contacts/{id}/photos
# ===========================================================================

class TestUploadPhoto:
    """POST /api/contacts/{id}/photos"""

    def test_upload_photo_success(self, client, create_user, db_session):
        """Upload photo successfully - owner can upload."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        # Use the same user to authenticate
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        
        jpeg = _make_jpeg()
        resp = client.post(
            f"/api/contacts/{contact.id}/photos",
            headers=headers,
            files={"file": ("photo.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 201

    def test_upload_photo_nonexistent_contact(self, client, create_user, db_session):
        """Upload photo to non-existent contact returns 404."""
        user = create_user()
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        jpeg = _make_jpeg()

        resp = client.post(
            "/api/contacts/99999/photos",
            headers=headers,
            files={"file": ("photo.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 404

    def test_upload_photo_non_owner_rejected(self, client, create_user, db_session):
        """Non-owner cannot upload photos."""
        owner = create_user(username="owner", email="owner@test.com")
        stranger = create_user(username="stranger", email="stranger@test.com")
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        # Authenticate as stranger
        token = create_token(stranger.id)
        headers = {"Authorization": f"Bearer {token}"}
        
        jpeg = _make_jpeg()
        resp = client.post(
            f"/api/contacts/{contact.id}/photos",
            headers=headers,
            files={"file": ("photo.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 403


# ===========================================================================
# PHOTOS: DELETE /api/contacts/{id}/photos/{photo_id}
# ===========================================================================

class TestDeletePhoto:
    """DELETE /api/contacts/{id}/photos/{photo_id}"""

    def test_delete_photo_success(self, client, create_user, db_session):
        """Owner can delete their photo."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        photo = ContactPhoto(contact_id=contact.id, photo_path="/uploads/test.jpg", caption="Test", sort_order=1)
        db_session.add(photo)
        db_session.commit()
        db_session.refresh(photo)

        # Authenticate as owner
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = client.delete(f"/api/contacts/{contact.id}/photos/{photo.id}", headers=headers)
        assert resp.status_code in [200, 204]

    def test_delete_photo_non_owner_rejected(self, client, create_user, db_session):
        """Non-owner cannot delete photos."""
        owner = create_user(username="owner_del", email="owner_del@test.com")
        stranger = create_user(username="stranger_del", email="stranger_del@test.com")
        
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        photo = ContactPhoto(contact_id=contact.id, photo_path="/uploads/test.jpg", caption="Test", sort_order=1)
        db_session.add(photo)
        db_session.commit()
        db_session.refresh(photo)

        # Authenticate as stranger
        token = create_token(stranger.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.delete(f"/api/contacts/{contact.id}/photos/{photo.id}", headers=headers)
        assert resp.status_code == 403


# ===========================================================================
# SCHEDULES: GET /api/contacts/{id}/schedules
# ===========================================================================

class TestListSchedules:
    """GET /api/contacts/{id}/schedules"""

    def test_list_schedules_empty(self, client, create_user, db_session):
        """List schedules for contact with no schedules."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        resp = client.get(f"/api/contacts/{contact.id}/schedules")
        assert resp.status_code == 200

    def test_list_schedules_with_data(self, client, create_user, db_session):
        """List schedules for contact with schedules."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        schedule = Schedule(contact_id=contact.id, day_of_week=0, open_time="08:00", close_time="18:00")
        db_session.add(schedule)
        db_session.commit()

        resp = client.get(f"/api/contacts/{contact.id}/schedules")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1


# ===========================================================================
# SCHEDULES: PUT /api/contacts/{id}/schedules
# ===========================================================================

class TestUpdateSchedules:
    """PUT /api/contacts/{id}/schedules"""

    def test_update_schedules_success(self, client, create_user, db_session):
        """Owner can update schedules."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        # Authenticate as owner
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = client.put(
            f"/api/contacts/{contact.id}/schedules",
            headers=headers,
            json=[
                {"day_of_week": 0, "open_time": "08:00", "close_time": "18:00"},
                {"day_of_week": 1, "open_time": "08:00", "close_time": "18:00"},
            ],
        )
        assert resp.status_code == 200

    def test_update_schedules_non_owner_rejected(self, client, create_user, db_session):
        """Non-owner cannot update schedules."""
        owner = create_user(username="owner_sched", email="owner_sched@test.com")
        stranger = create_user(username="stranger_sched", email="stranger_sched@test.com")
        
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        # Authenticate as stranger
        token = create_token(stranger.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.put(
            f"/api/contacts/{contact.id}/schedules",
            headers=headers,
            json=[{"day_of_week": 0, "open_time": "08:00", "close_time": "18:00"}],
        )
        assert resp.status_code == 403


# ===========================================================================
# RELATED: GET /api/contacts/{id}/related
# ===========================================================================

class TestRelatedContacts:
    """GET /api/contacts/{id}/related"""

    def test_related_contacts_same_category(self, client, create_user, db_session):
        """Related contacts in same category are returned."""
        user = create_user()
        
        # Get a category
        cat = db_session.query(Category).first()
        
        contact1 = Contact(name="Biz 1", phone="1234567", user_id=user.id, category_id=cat.id)
        contact2 = Contact(name="Biz 2", phone="2234567", user_id=user.id, category_id=cat.id)
        db_session.add(contact1)
        db_session.add(contact2)
        db_session.commit()

        resp = client.get(f"/api/contacts/{contact1.id}/related")
        assert resp.status_code == 200


# ===========================================================================
# ADDITIONAL PHOTOS TESTS
# ===========================================================================

class TestUploadPhotoAdditional:
    """Additional photo upload tests."""

    def test_upload_photo_invalid_extension(self, client, create_user, db_session):
        """PNG files should be rejected."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        png_buf = io.BytesIO()
        Image.new("RGB", (100, 100)).save(png_buf, format="PNG")
        png_buf.seek(0)

        resp = client.post(
            f"/api/contacts/{contact.id}/photos",
            headers=headers,
            files={"file": ("photo.png", png_buf, "image/png")},
        )
        assert resp.status_code == 400

    def test_upload_photo_invalid_jpeg_magic(self, client, create_user, db_session):
        """Non-JPEG data should be rejected."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        fake = io.BytesIO(b"NOT_JPEG_DATA_AT_ALL")

        resp = client.post(
            f"/api/contacts/{contact.id}/photos",
            headers=headers,
            files={"file": ("photo.jpg", fake, "image/jpeg")},
        )
        assert resp.status_code == 400

    def test_upload_photo_max_five(self, client, create_user, db_session):
        """Maximum 5 photos per contact."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        # Pre-insert 5 photos
        for i in range(5):
            db_session.add(ContactPhoto(
                contact_id=contact.id, photo_path=f"/uploads/img_{i}.jpg", sort_order=i+1
            ))
        db_session.commit()

        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        jpeg = _make_jpeg()

        resp = client.post(
            f"/api/contacts/{contact.id}/photos",
            headers=headers,
            files={"file": ("photo.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 400

    def test_upload_photo_requires_auth(self, client, create_user, db_session):
        """Photo upload requires authentication."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        jpeg = _make_jpeg()
        resp = client.post(
            f"/api/contacts/{contact.id}/photos",
            files={"file": ("photo.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 401


# ===========================================================================
# ADDITIONAL SCHEDULES TESTS
# ===========================================================================

class TestUpdateSchedulesAdditional:
    """Additional schedule update tests."""

    def test_update_schedules_replaces_old(self, client, create_user, db_session):
        """Updating schedules replaces old ones."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        # Add initial schedule
        db_session.add(Schedule(contact_id=contact.id, day_of_week=0, open_time="08:00", close_time="12:00"))
        db_session.commit()

        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.put(
            f"/api/contacts/{contact.id}/schedules",
            headers=headers,
            json=[{"day_of_week": 1, "open_time": "10:00", "close_time": "20:00"}],
        )
        assert resp.status_code == 200

        # Old schedule should be gone
        resp = client.get(f"/api/contacts/{contact.id}/schedules")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["day_of_week"] == 1

    def test_update_schedules_invalid_day_rejected(self, client, create_user, db_session):
        """Invalid day_of_week values should be rejected."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.put(
            f"/api/contacts/{contact.id}/schedules",
            headers=headers,
            json=[
                {"day_of_week": 7, "open_time": "09:00", "close_time": "17:00"},  # Invalid
                {"day_of_week": 0, "open_time": "09:00", "close_time": "17:00"},  # Valid
            ],
        )
        assert resp.status_code == 422


# ===========================================================================
# RELATED BUSINESSES ADDITIONAL TESTS
# ===========================================================================

class TestRelatedBusinessesAdditional:
    """Additional related businesses tests."""

    def test_related_returns_empty_no_coords(self, client, create_user, db_session):
        """Contact without lat/lon should return empty list."""
        user = create_user()
        cat = db_session.query(Category).first()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id, category_id=cat.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        resp = client.get(f"/api/contacts/{contact.id}/related")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_related_returns_empty_no_category(self, client, create_user, db_session):
        """Contact without category should return empty list."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id, latitude=-32.95, longitude=-60.66)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        resp = client.get(f"/api/contacts/{contact.id}/related")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_related_finds_same_category_nearby(self, client, create_user, db_session):
        """Related finds contacts in same category nearby."""
        user = create_user()
        cat = db_session.query(Category).first()
        cat_id = cat.id
        
        main = Contact(name="Main", phone="1111111", user_id=user.id, category_id=cat_id,
                       latitude=-32.950, longitude=-60.660, status="active")
        near = Contact(name="Near", phone="2222222", user_id=user.id, category_id=cat_id,
                       latitude=-32.951, longitude=-60.661, status="active")
        far = Contact(name="Far", phone="3333333", user_id=user.id, category_id=cat_id,
                      latitude=-34.000, longitude=-58.000, status="active")
        other_cat = Contact(name="OtherCat", phone="4444444", user_id=user.id, category_id=cat_id + 1,
                            latitude=-32.951, longitude=-60.661, status="active")
        db_session.add_all([main, near, far, other_cat])
        db_session.commit()
        db_session.refresh(main)

        resp = client.get(f"/api/contacts/{main.id}/related?radius_km=5")
        assert resp.status_code == 200
        data = resp.json()
        names = [c["name"] for c in data]
        assert "Near" in names
        assert "Far" not in names
        assert "OtherCat" not in names

    def test_related_nonexistent_contact(self, client):
        """Related for non-existent contact returns 404."""
        resp = client.get("/api/contacts/99999/related")
        assert resp.status_code == 404

    def test_related_excludes_self(self, client, create_user, db_session):
        """Related should not include the contact itself."""
        user = create_user()
        cat = db_session.query(Category).first()
        contact = Contact(name="Self", phone="1234567", user_id=user.id, category_id=cat.id,
                          latitude=-32.950, longitude=-60.660)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        resp = client.get(f"/api/contacts/{contact.id}/related")
        assert resp.status_code == 200
        data = resp.json()
        assert all(c["id"] != contact.id for c in data)


# ===========================================================================
# DELETE PHOTO ADDITIONAL TESTS
# ===========================================================================

class TestDeletePhotoAdditional:
    """Additional delete photo tests."""

    def test_delete_photo_not_found(self, client, create_user, db_session):
        """Deleting non-existent photo returns 404."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.delete(f"/api/contacts/{contact.id}/photos/99999", headers=headers)
        assert resp.status_code == 404

    def test_delete_photo_contact_not_found(self, client, create_user, db_session):
        """Deleting photo from non-existent contact returns 404."""
        user = create_user()
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.delete("/api/contacts/99999/photos/1", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# UPDATE SCHEDULES ADDITIONAL TESTS
# ===========================================================================

class TestUpdateSchedulesAdditional2:
    """Additional schedule update tests."""

    def test_update_schedules_nonexistent(self, client, create_user, db_session):
        """Updating schedules for non-existent contact returns 404."""
        user = create_user()
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.put(
            "/api/contacts/99999/schedules",
            headers=headers,
            json=[{"day_of_week": 0, "open_time": "09:00", "close_time": "17:00"}],
        )
        assert resp.status_code == 404


# ===========================================================================
# CANCEL DELETION TESTS
# ===========================================================================

class TestCancelDeletion:
    """POST /api/contacts/{id}/cancel-deletion"""

    def test_cancel_deletion_success(self, client, create_user, db_session):
        """Owner can cancel deletion of flagged contact."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id, status="flagged")
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(f"/api/contacts/{contact.id}/cancel-deletion", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_cancel_deletion_not_flagged(self, client, create_user, db_session):
        """Cancel deletion on non-flagged contact returns 400."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id, status="active")
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(f"/api/contacts/{contact.id}/cancel-deletion", headers=headers)
        assert resp.status_code == 400

    def test_cancel_deletion_non_owner_non_admin(self, client, create_user, db_session):
        """Non-owner non-admin cannot cancel deletion."""
        owner = create_user(username="owner_cd", email="owner_cd@test.com")
        stranger = create_user(username="stranger_cd", email="stranger_cd@test.com")
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id, status="flagged")
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(stranger.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(f"/api/contacts/{contact.id}/cancel-deletion", headers=headers)
        assert resp.status_code == 403

    def test_cancel_deletion_admin_can_cancel(self, client, admin_user, create_user, db_session):
        """Admin can cancel deletion of any contact."""
        owner = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id, status="flagged")
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(admin_user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(f"/api/contacts/{contact.id}/cancel-deletion", headers=headers)
        assert resp.status_code == 200

    def test_cancel_deletion_contact_not_found(self, client, create_user, db_session):
        """Cancel deletion for non-existent contact returns 404."""
        user = create_user()
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/contacts/99999/cancel-deletion", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# REQUEST DELETION EDGE CASES
# ===========================================================================

class TestRequestDeletionEdgeCases:
    """POST /api/contacts/{id}/request-deletion"""

    def test_request_deletion_already_flagged(self, client, create_user, db_session):
        """Requesting deletion on already flagged contact returns 400."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id, status="flagged")
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(f"/api/contacts/{contact.id}/request-deletion", headers=headers)
        assert resp.status_code == 400

    def test_request_deletion_contact_not_found(self, client, create_user, db_session):
        """Requesting deletion for non-existent contact returns 404."""
        user = create_user()
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/contacts/99999/request-deletion", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# DELETE CONTACT WITH PHOTO CLEANUP
# ===========================================================================

class TestDeleteContactWithPhoto:
    """DELETE /api/contacts/{id}"""

    def test_admin_can_delete_any_contact(self, client, admin_user, create_user, db_session):
        """Admin can delete any contact."""
        owner = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(admin_user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.delete(f"/api/contacts/{contact.id}", headers=headers)
        assert resp.status_code == 204


# ===========================================================================
# VERIFY CHANGE EDGE CASES
# ===========================================================================

class TestVerifyChangeEdgeCases:
    """POST /api/contacts/{id}/changes/{cid}/verify"""

    def test_verify_change_contact_not_found(self, client, create_user, db_session):
        """Verify change for non-existent contact returns 404."""
        user = create_user()
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/contacts/99999/changes/1/verify", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# REJECT CHANGE EDGE CASES
# ===========================================================================

class TestRejectChangeEdgeCases:
    """POST /api/contacts/{id}/changes/{cid}/reject"""

    def test_reject_change_contact_not_found(self, client, create_user, db_session):
        """Reject change for non-existent contact returns 404."""
        user = create_user()
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/contacts/99999/changes/1/reject", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# HISTORY EDGE CASES
# ===========================================================================

class TestHistoryEdgeCases:
    """GET /api/contacts/{id}/history"""

    def test_history_contact_not_found(self, client, create_user, db_session):
        """History for non-existent contact returns 404."""
        user = create_user()
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/contacts/99999/history", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# CHANGES EDGE CASES
# ===========================================================================

class TestChangesEdgeCases:
    """GET /api/contacts/{id}/changes"""

    def test_changes_contact_not_found(self, client, create_user, db_session):
        """Changes for non-existent contact returns 404."""
        user = create_user()
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/contacts/99999/changes", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# DELETE CHANGE EDGE CASES
# ===========================================================================

class TestDeleteChangeEdgeCases:
    """DELETE /api/contacts/{id}/changes/{cid}"""

    def test_delete_change_contact_not_found(self, client, create_user, db_session):
        """Delete change for non-existent contact returns 404."""
        user = create_user()
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.delete("/api/contacts/99999/changes/1", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# REGISTER LEAD EDGE CASES
# ===========================================================================

class TestRegisterLeadEdgeCases:
    """POST /api/contacts/{id}/leads"""

    def test_lead_contact_not_found(self, client):
        """Register lead for non-existent contact returns 404."""
        resp = client.post("/api/contacts/99999/leads")
        assert resp.status_code == 404


# ===========================================================================
# GET LEADS EDGE CASES
# ===========================================================================

class TestGetLeadsEdgeCases:
    """GET /api/contacts/{id}/leads"""

    def test_leads_contact_not_found(self, client, create_user, db_session):
        """Get leads for non-existent contact returns 404."""
        user = create_user()
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/contacts/99999/leads", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# DELETE IMAGE EDGE CASES
# ===========================================================================

class TestDeleteImageEdgeCases:
    """DELETE /api/contacts/{id}/image"""

    def test_delete_image_contact_not_found(self, client, create_user, db_session):
        """Delete image for non-existent contact returns 404."""
        user = create_user()
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.delete("/api/contacts/99999/image", headers=headers)
        assert resp.status_code == 404

    def test_delete_image_no_photo(self, client, create_user, db_session):
        """Delete image when contact has no photo returns 404."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.delete(f"/api/contacts/{contact.id}/image", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# VERIFY CONTACT EDGE CASES
# ===========================================================================

class TestVerifyContactEdgeCases:
    """POST /api/contacts/{id}/verify"""

    def test_verify_contact_not_found(self, client, create_user, db_session):
        """Verify non-existent contact returns 404."""
        user = create_user()
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/contacts/99999/verify", headers=headers, json={"is_verified": True})
        assert resp.status_code == 404


# ===========================================================================
# UPLOAD CONTACT IMAGE EDGE CASES
# ===========================================================================

class TestUploadContactImageFull:
    """POST /api/contacts/{id}/image"""

    def test_upload_image_nonexistent_contact(self, client, create_user, db_session):
        """Upload image to non-existent contact returns 404."""
        user = create_user()
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        jpeg = _make_jpeg()
        resp = client.post(
            "/api/contacts/99999/image",
            headers=headers,
            files={"file": ("test.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 404

    def test_upload_image_large_resized(self, client, create_user, db_session):
        """Large image should be resized."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        # Create image larger than 1024x1024
        big_jpeg = _make_jpeg(width=2000, height=1500)

        resp = client.post(
            f"/api/contacts/{contact.id}/image",
            headers=headers,
            files={"file": ("big.jpg", big_jpeg, "image/jpeg")},
        )
        assert resp.status_code == 200
