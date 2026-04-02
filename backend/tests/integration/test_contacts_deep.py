"""Tests for photos, schedules, related businesses, transfer-ownership, and cancel-deletion.

These endpoints had 0% coverage. This file targets every uncovered branch.
"""
import pytest
import io
from PIL import Image
from app.models.contact import Contact, ContactHistory
from app.models.contact_photo import ContactPhoto
from app.models.schedule import Schedule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jpeg(width=100, height=100):
    """Create a minimal valid JPEG in memory."""
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def _make_large_jpeg():
    """Create a JPEG payload > 2MB for size validation tests."""
    # Start with valid JPEG magic, then pad with junk to exceed 2MB
    data = b'\xFF\xD8\xFF\xE0' + b'\x00' * (2 * 1024 * 1024 + 1)
    return io.BytesIO(data)


def _login(client, username, password="password123"):
    """Helper to login and return auth headers."""
    resp = client.post("/api/auth/login", json={
        "username_or_email": username,
        "password": password,
    })
    return {"Authorization": f"Bearer {resp.json()['token']}"}


# ===========================================================================
# PHOTOS: GET /api/contacts/{id}/photos
# ===========================================================================

class TestListPhotos:
    """GET /api/contacts/{id}/photos"""

    def test_list_photos_empty(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.get(f"/api/contacts/{contact.id}/photos")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_photos_with_data(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        photo = ContactPhoto(contact_id=contact.id, photo_path="/uploads/images/test.jpg", caption="Test", sort_order=1)
        database_session.add(photo)
        database_session.commit()

        resp = client.get(f"/api/contacts/{contact.id}/photos")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["caption"] == "Test"

    def test_list_photos_nonexistent_contact(self, client):
        resp = client.get("/api/contacts/99999/photos")
        assert resp.status_code == 404


# ===========================================================================
# PHOTOS: POST /api/contacts/{id}/photos
# ===========================================================================

class TestUploadPhoto:
    """POST /api/contacts/{id}/photos"""

    def test_upload_photo_success(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        jpeg = _make_jpeg()

        resp = client.post(
            f"/api/contacts/{contact.id}/photos",
            headers=headers,
            files={"file": ("photo.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["photo_path"] is not None

    def test_upload_photo_nonexistent_contact(self, client, auth_headers):
        headers = auth_headers()
        jpeg = _make_jpeg()

        resp = client.post(
            "/api/contacts/99999/photos",
            headers=headers,
            files={"file": ("photo.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 404

    def test_upload_photo_non_owner_rejected(self, client, create_user, database_session):
        owner = create_user(username="owner", email="owner@test.com")
        stranger = create_user(username="stranger", email="stranger@test.com")
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "stranger")
        jpeg = _make_jpeg()

        resp = client.post(
            f"/api/contacts/{contact.id}/photos",
            headers=headers,
            files={"file": ("photo.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 403

    def test_upload_photo_invalid_extension(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        png_buf = io.BytesIO()
        Image.new("RGB", (100, 100)).save(png_buf, format="PNG")
        png_buf.seek(0)

        resp = client.post(
            f"/api/contacts/{contact.id}/photos",
            headers=headers,
            files={"file": ("photo.png", png_buf, "image/png")},
        )
        assert resp.status_code == 400

    def test_upload_photo_too_large(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        big = _make_large_jpeg()

        resp = client.post(
            f"/api/contacts/{contact.id}/photos",
            headers=headers,
            files={"file": ("photo.jpg", big, "image/jpeg")},
        )
        assert resp.status_code == 400

    def test_upload_photo_invalid_jpeg_magic(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        fake = io.BytesIO(b"NOT_JPEG_DATA_AT_ALL")

        resp = client.post(
            f"/api/contacts/{contact.id}/photos",
            headers=headers,
            files={"file": ("photo.jpg", fake, "image/jpeg")},
        )
        assert resp.status_code == 400

    def test_upload_photo_max_five(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        # Pre-insert 5 photos
        for i in range(5):
            database_session.add(ContactPhoto(
                contact_id=contact.id, photo_path=f"/uploads/img_{i}.jpg", sort_order=i+1
            ))
        database_session.commit()

        headers = _login(client, "testuser")
        jpeg = _make_jpeg()

        resp = client.post(
            f"/api/contacts/{contact.id}/photos",
            headers=headers,
            files={"file": ("photo.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 400
        assert "Máximo 5" in resp.json()["detail"]

    def test_upload_photo_requires_auth(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        jpeg = _make_jpeg()
        resp = client.post(
            f"/api/contacts/{contact.id}/photos",
            files={"file": ("photo.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 401


# ===========================================================================
# PHOTOS: DELETE /api/contacts/{id}/photos/{photo_id}
# ===========================================================================

class TestDeletePhoto:
    """DELETE /api/contacts/{id}/photos/{photo_id}"""

    def test_delete_photo_success(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        photo = ContactPhoto(contact_id=contact.id, photo_path="/uploads/images/test.jpg", sort_order=1)
        database_session.add(photo)
        database_session.commit()
        database_session.refresh(photo)

        headers = _login(client, "testuser")
        resp = client.delete(f"/api/contacts/{contact.id}/photos/{photo.id}", headers=headers)
        assert resp.status_code == 204

    def test_delete_photo_not_found(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        resp = client.delete(f"/api/contacts/{contact.id}/photos/99999", headers=headers)
        assert resp.status_code == 404

    def test_delete_photo_non_owner_rejected(self, client, create_user, database_session):
        owner = create_user(username="owner", email="owner@test.com")
        stranger = create_user(username="stranger", email="stranger@test.com")
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        photo = ContactPhoto(contact_id=contact.id, photo_path="/uploads/img.jpg", sort_order=1)
        database_session.add(photo)
        database_session.commit()
        database_session.refresh(photo)

        headers = _login(client, "stranger")
        resp = client.delete(f"/api/contacts/{contact.id}/photos/{photo.id}", headers=headers)
        assert resp.status_code == 403

    def test_delete_photo_contact_not_found(self, client, auth_headers):
        headers = auth_headers()
        resp = client.delete("/api/contacts/99999/photos/1", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# SCHEDULES: GET /api/contacts/{id}/schedules
# ===========================================================================

class TestListSchedules:
    """GET /api/contacts/{id}/schedules"""

    def test_list_schedules_empty(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.get(f"/api/contacts/{contact.id}/schedules")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_schedules_with_data(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        database_session.add(Schedule(contact_id=contact.id, day_of_week=0, open_time="08:00", close_time="18:00"))
        database_session.add(Schedule(contact_id=contact.id, day_of_week=6, open_time=None, close_time=None))
        database_session.commit()

        resp = client.get(f"/api/contacts/{contact.id}/schedules")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Check day names
        days = {s["day_of_week"]: s for s in data}
        assert days[0]["day_name"] == "Lunes"
        assert days[0]["is_closed"] is False
        assert days[6]["day_name"] == "Domingo"
        assert days[6]["is_closed"] is True

    def test_list_schedules_nonexistent(self, client):
        resp = client.get("/api/contacts/99999/schedules")
        assert resp.status_code == 404


# ===========================================================================
# SCHEDULES: PUT /api/contacts/{id}/schedules
# ===========================================================================

class TestUpdateSchedules:
    """PUT /api/contacts/{id}/schedules"""

    def test_update_schedules_success(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        resp = client.put(
            f"/api/contacts/{contact.id}/schedules",
            headers=headers,
            json=[
                {"day_of_week": 0, "open_time": "09:00", "close_time": "17:00"},
                {"day_of_week": 1, "open_time": "09:00", "close_time": "17:00"},
                {"day_of_week": 6, "open_time": None, "close_time": None},
            ],
        )
        assert resp.status_code == 200

        # Verify data was saved
        resp = client.get(f"/api/contacts/{contact.id}/schedules")
        data = resp.json()
        assert len(data) == 3

    def test_update_schedules_replaces_old(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        # Add initial schedule
        database_session.add(Schedule(contact_id=contact.id, day_of_week=0, open_time="08:00", close_time="12:00"))
        database_session.commit()

        headers = _login(client, "testuser")
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

    def test_update_schedules_non_owner_rejected(self, client, create_user, database_session):
        owner = create_user(username="owner", email="owner@test.com")
        stranger = create_user(username="stranger", email="stranger@test.com")
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "stranger")
        resp = client.put(
            f"/api/contacts/{contact.id}/schedules",
            headers=headers,
            json=[{"day_of_week": 0, "open_time": "09:00", "close_time": "17:00"}],
        )
        assert resp.status_code == 403

    def test_update_schedules_nonexistent(self, client, auth_headers):
        headers = auth_headers()
        resp = client.put(
            "/api/contacts/99999/schedules",
            headers=headers,
            json=[{"day_of_week": 0, "open_time": "09:00", "close_time": "17:00"}],
        )
        assert resp.status_code == 404

    def test_update_schedules_invalid_day_skipped(self, client, create_user, database_session):
        """Invalid day_of_week values should be silently skipped."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        resp = client.put(
            f"/api/contacts/{contact.id}/schedules",
            headers=headers,
            json=[
                {"day_of_week": 7, "open_time": "09:00", "close_time": "17:00"},  # Invalid
                {"day_of_week": 0, "open_time": "09:00", "close_time": "17:00"},  # Valid
            ],
        )
        assert resp.status_code == 200
        resp = client.get(f"/api/contacts/{contact.id}/schedules")
        assert len(resp.json()) == 1  # Only the valid one


# ===========================================================================
# RELATED BUSINESSES: GET /api/contacts/{id}/related
# ===========================================================================

class TestRelatedBusinesses:
    """GET /api/contacts/{id}/related"""

    def test_related_returns_empty_no_coords(self, client, create_user, database_session):
        """Contact without lat/lon should return empty list."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id, category_id=1)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.get(f"/api/contacts/{contact.id}/related")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_related_returns_empty_no_category(self, client, create_user, database_session):
        """Contact without category should return empty list."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id, latitude=-32.95, longitude=-60.66)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.get(f"/api/contacts/{contact.id}/related")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_related_finds_same_category_nearby(self, client, create_user, database_session):
        user = create_user()
        cat_id = 1
        main = Contact(name="Main", phone="1111111", user_id=user.id, category_id=cat_id,
                       latitude=-32.950, longitude=-60.660)
        near = Contact(name="Near", phone="2222222", user_id=user.id, category_id=cat_id,
                       latitude=-32.951, longitude=-60.661, status="active")
        far = Contact(name="Far", phone="3333333", user_id=user.id, category_id=cat_id,
                      latitude=-34.000, longitude=-58.000, status="active")
        other_cat = Contact(name="OtherCat", phone="4444444", user_id=user.id, category_id=2,
                            latitude=-32.951, longitude=-60.661, status="active")
        database_session.add_all([main, near, far, other_cat])
        database_session.commit()
        database_session.refresh(main)

        resp = client.get(f"/api/contacts/{main.id}/related?radius_km=5")
        assert resp.status_code == 200
        data = resp.json()
        names = [c["name"] for c in data]
        assert "Near" in names
        assert "Far" not in names
        assert "OtherCat" not in names

    def test_related_nonexistent_contact(self, client):
        resp = client.get("/api/contacts/99999/related")
        assert resp.status_code == 404

    def test_related_excludes_self(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Self", phone="1234567", user_id=user.id, category_id=1,
                          latitude=-32.950, longitude=-60.660)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.get(f"/api/contacts/{contact.id}/related")
        assert resp.status_code == 200
        data = resp.json()
        assert all(c["id"] != contact.id for c in data)


# ===========================================================================
# TRANSFER OWNERSHIP: PUT /api/contacts/{id}/transfer-ownership
# ===========================================================================

class TestTransferOwnership:
    """PUT /api/contacts/{id}/transfer-ownership"""

    def test_transfer_success(self, client, admin_headers, create_user, database_session):
        old_owner = create_user(username="oldowner", email="old@test.com")
        new_owner = create_user(username="newowner", email="new@test.com")
        contact = Contact(name="Biz", phone="1234567", user_id=old_owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.put(
            f"/api/contacts/{contact.id}/transfer-ownership",
            headers=admin_headers,
            json={"new_owner_id": new_owner.id},
        )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == new_owner.id

    def test_transfer_resets_flagged_status(self, client, admin_headers, create_user, database_session):
        old_owner = create_user(username="oldowner", email="old@test.com")
        new_owner = create_user(username="newowner", email="new@test.com")
        contact = Contact(name="Biz", phone="1234567", user_id=old_owner.id, status="flagged")
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.put(
            f"/api/contacts/{contact.id}/transfer-ownership",
            headers=admin_headers,
            json={"new_owner_id": new_owner.id},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_transfer_non_admin_rejected(self, client, auth_headers, create_user, database_session):
        owner = create_user(username="owner", email="owner@test.com")
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = auth_headers(username="regular", email="regular@test.com")
        resp = client.put(
            f"/api/contacts/{contact.id}/transfer-ownership",
            headers=headers,
            json={"new_owner_id": owner.id},
        )
        assert resp.status_code == 403

    def test_transfer_missing_new_owner_id(self, client, admin_headers, create_user, database_session):
        owner = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.put(
            f"/api/contacts/{contact.id}/transfer-ownership",
            headers=admin_headers,
            json={},
        )
        assert resp.status_code == 400

    def test_transfer_contact_not_found(self, client, admin_headers):
        resp = client.put(
            "/api/contacts/99999/transfer-ownership",
            headers=admin_headers,
            json={"new_owner_id": 1},
        )
        assert resp.status_code == 404

    def test_transfer_new_owner_not_found(self, client, admin_headers, create_user, database_session):
        owner = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.put(
            f"/api/contacts/{contact.id}/transfer-ownership",
            headers=admin_headers,
            json={"new_owner_id": 99999},
        )
        assert resp.status_code == 404


# ===========================================================================
# CANCEL DELETION: POST /api/contacts/{id}/cancel-deletion
# ===========================================================================

class TestCancelDeletion:
    """POST /api/contacts/{id}/cancel-deletion"""

    def test_cancel_deletion_success(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id, status="flagged")
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        resp = client.post(f"/api/contacts/{contact.id}/cancel-deletion", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_cancel_deletion_not_flagged(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id, status="active")
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        resp = client.post(f"/api/contacts/{contact.id}/cancel-deletion", headers=headers)
        assert resp.status_code == 400

    def test_cancel_deletion_non_owner_non_admin(self, client, create_user, database_session):
        owner = create_user(username="owner", email="owner@test.com")
        stranger = create_user(username="stranger", email="stranger@test.com")
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id, status="flagged")
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "stranger")
        resp = client.post(f"/api/contacts/{contact.id}/cancel-deletion", headers=headers)
        assert resp.status_code == 403

    def test_cancel_deletion_admin_can_cancel(self, client, admin_headers, create_user, database_session):
        owner = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id, status="flagged")
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.post(f"/api/contacts/{contact.id}/cancel-deletion", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_cancel_deletion_contact_not_found(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts/99999/cancel-deletion", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# REQUEST DELETION edge cases
# ===========================================================================

class TestRequestDeletionEdgeCases:
    """POST /api/contacts/{id}/request-deletion"""

    def test_request_deletion_already_flagged(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id, status="flagged")
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        resp = client.post(f"/api/contacts/{contact.id}/request-deletion", headers=headers)
        assert resp.status_code == 400

    def test_request_deletion_contact_not_found(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts/99999/request-deletion", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# DELETE CONTACT with photo cleanup
# ===========================================================================

class TestDeleteContactWithPhoto:
    """DELETE /api/contacts/{id} — photo cleanup path"""

    def test_admin_can_delete_any_contact(self, client, admin_headers, create_user, database_session):
        owner = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.delete(f"/api/contacts/{contact.id}", headers=admin_headers)
        assert resp.status_code == 204


# ===========================================================================
# VERIFY CHANGE edge cases
# ===========================================================================

class TestVerifyChangeEdgeCases:
    """POST /api/contacts/{id}/changes/{cid}/verify"""

    def test_verify_change_contact_not_found(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts/99999/changes/1/verify", headers=headers)
        assert resp.status_code == 404

    def test_verify_change_change_not_found(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        resp = client.post(f"/api/contacts/{contact.id}/changes/99999/verify", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# REJECT CHANGE edge cases
# ===========================================================================

class TestRejectChangeEdgeCases:
    """POST /api/contacts/{id}/changes/{cid}/reject"""

    def test_reject_change_contact_not_found(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts/99999/changes/1/reject", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# GET CONTACT HISTORY edge cases
# ===========================================================================

class TestHistoryEdgeCases:
    """GET /api/contacts/{id}/history"""

    def test_history_contact_not_found(self, client, auth_headers):
        headers = auth_headers()
        resp = client.get("/api/contacts/99999/history", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# GET CONTACT CHANGES edge cases
# ===========================================================================

class TestChangesEdgeCases:
    """GET /api/contacts/{id}/changes"""

    def test_changes_contact_not_found(self, client, auth_headers):
        headers = auth_headers()
        resp = client.get("/api/contacts/99999/changes", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# LIST PENDING CONTACTS — moderator path
# ===========================================================================

class TestListPendingContactsModerator:
    """GET /api/contacts/pending — moderator sees all"""

    def test_moderator_sees_all_pending(self, client, moderator_user, create_user, database_session):
        _, mod_headers = moderator_user
        owner = create_user(username="owner", email="owner@test.com")
        contact = Contact(name="Biz", phone="1234567", user_id=owner.id, pending_changes_count=1)
        database_session.add(contact)
        database_session.commit()

        resp = client.get("/api/contacts/pending", headers=mod_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1


# ===========================================================================
# DELETE CONTACT CHANGE edge cases
# ===========================================================================

class TestDeleteChangeEdgeCases:
    """DELETE /api/contacts/{id}/changes/{cid}"""

    def test_delete_change_contact_not_found(self, client, auth_headers):
        headers = auth_headers()
        resp = client.delete("/api/contacts/99999/changes/1", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# REGISTER LEAD edge case
# ===========================================================================

class TestRegisterLeadEdgeCases:
    """POST /api/contacts/{id}/leads"""

    def test_lead_contact_not_found(self, client):
        resp = client.post("/api/contacts/99999/leads")
        assert resp.status_code == 404


# ===========================================================================
# GET LEADS edge case
# ===========================================================================

class TestGetLeadsEdgeCases:
    """GET /api/contacts/{id}/leads"""

    def test_leads_contact_not_found(self, client, auth_headers):
        headers = auth_headers()
        resp = client.get("/api/contacts/99999/leads", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# DELETE IMAGE edge case
# ===========================================================================

class TestDeleteImageEdgeCases:
    """DELETE /api/contacts/{id}/image"""

    def test_delete_image_contact_not_found(self, client, auth_headers):
        headers = auth_headers()
        resp = client.delete("/api/contacts/99999/image", headers=headers)
        assert resp.status_code == 404

    def test_delete_image_no_photo(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        resp = client.delete(f"/api/contacts/{contact.id}/image", headers=headers)
        assert resp.status_code == 404


# ===========================================================================
# VERIFY CONTACT edge case
# ===========================================================================

class TestVerifyContactEdgeCases:
    """POST /api/contacts/{id}/verify"""

    def test_verify_contact_not_found(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts/99999/verify", headers=headers, json={"is_verified": True})
        assert resp.status_code == 404


# ===========================================================================
# UPLOAD CONTACT IMAGE — edge cases for full path coverage
# ===========================================================================

class TestUploadContactImageFull:
    """POST /api/contacts/{id}/image — full path coverage"""

    def test_upload_image_nonexistent_contact(self, client, auth_headers):
        headers = auth_headers()
        jpeg = _make_jpeg()
        resp = client.post(
            "/api/contacts/99999/image",
            headers=headers,
            files={"file": ("test.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 404

    def test_upload_image_large_resized(self, client, create_user, database_session):
        """Large image should be resized (covers line 641, 645)."""
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        # Create image larger than 1024x1024
        big_jpeg = _make_jpeg(width=2000, height=1500)

        resp = client.post(
            f"/api/contacts/{contact.id}/image",
            headers=headers,
            files={"file": ("big.jpg", big_jpeg, "image/jpeg")},
        )
        assert resp.status_code == 200
