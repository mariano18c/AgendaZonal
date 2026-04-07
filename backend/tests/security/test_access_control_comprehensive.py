"""Comprehensive access control and authorization tests - adapted."""
import pytest
import uuid
import bcrypt
from app.models.contact import Contact
from app.models.user import User
from app.auth import create_token


class TestOwnerOnlyEndpoints:
    """Verify that owner-only endpoints reject non-owners."""

    def test_non_owner_cannot_update_contact(self, client, create_user, db_session):
        """Non-owner should not be able to update contact."""
        uid = uuid.uuid4().hex[:8]
        owner = create_user(username=f"owner_{uid}", email=f"owner_{uid}@test.com")
        stranger = create_user(username=f"stranger_{uid}", email=f"stranger_{uid}@test.com")

        contact = Contact(name="Private Biz", phone="1234567", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(stranger.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.put(f"/api/contacts/{contact.id}", headers=headers, json={
            "name": "Hacked Name",
        })
        assert resp.status_code == 403

    def test_non_owner_cannot_delete_contact(self, client, create_user, db_session):
        """Non-owner should not be able to delete contact."""
        uid = uuid.uuid4().hex[:8]
        owner = create_user(username=f"owner2_{uid}", email=f"owner2_{uid}@test.com")
        stranger = create_user(username=f"stranger2_{uid}", email=f"stranger2_{uid}@test.com")

        contact = Contact(name="Private", phone="1234567", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(stranger.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.delete(f"/api/contacts/{contact.id}", headers=headers)
        assert resp.status_code == 403

    def test_owner_must_flag_before_delete(self, client, create_user, db_session):
        """Owner must flag contact before requesting deletion."""
        uid = uuid.uuid4().hex[:8]
        owner = create_user(username=f"owner3_{uid}", email=f"owner3_{uid}@test.com")
        
        contact = Contact(name="To Delete", phone="1234567", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(owner.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.delete(f"/api/contacts/{contact.id}", headers=headers)
        assert resp.status_code == 403
        # Should require flagging first

    def test_non_owner_cannot_request_deletion(self, client, create_user, db_session):
        """Non-owner should not be able to request deletion of contact."""
        uid = uuid.uuid4().hex[:8]
        owner = create_user(username=f"owner4_{uid}", email=f"owner4_{uid}@test.com")
        stranger = create_user(username=f"stranger4_{uid}", email=f"stranger4_{uid}@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(stranger.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post(f"/api/contacts/{contact.id}/request-deletion", headers=headers)
        assert resp.status_code == 403

    def test_non_owner_cannot_upload_photo(self, client, create_user, db_session):
        """Non-owner should not be able to upload photo to contact."""
        import io
        uid = uuid.uuid4().hex[:8]
        owner = create_user(username=f"owner5_{uid}", email=f"owner5_{uid}@test.com")
        stranger = create_user(username=f"stranger5_{uid}", email=f"stranger5_{uid}@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(stranger.id)
        headers = {"Authorization": f"Bearer {token}"}

        fake_jpeg = b'\xFF\xD8\xFF\xE0' + b'\x00' * 100
        resp = client.post(
            f"/api/contacts/{contact.id}/photos",
            headers=headers,
            files={"file": ("test.jpg", io.BytesIO(fake_jpeg), "image/jpeg")},
        )
        assert resp.status_code == 403

    def test_non_owner_cannot_update_schedule(self, client, create_user, db_session):
        """Non-owner should not be able to update contact schedule."""
        uid = uuid.uuid4().hex[:8]
        owner = create_user(username=f"owner6_{uid}", email=f"owner6_{uid}@test.com")
        stranger = create_user(username=f"stranger6_{uid}", email=f"stranger6_{uid}@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(stranger.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.put(
            f"/api/contacts/{contact.id}/schedules",
            headers=headers,
            json=[{"day_of_week": 0, "open_time": "08:00", "close_time": "18:00"}],
        )
        assert resp.status_code == 403


class TestModeratorPermissions:
    """Verify moderator permission boundaries."""

    def test_moderator_can_approve_reviews(self, client, create_user, db_session):
        """Moderator should be able to approve reviews."""
        from app.models.review import Review
        
        uid = uuid.uuid4().hex[:8]
        mod_user = User(
            username=f"mod_{uid}",
            email=f"mod_{uid}@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash=bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode(),
            role="moderator",
            is_active=True,
        )
        db_session.add(mod_user)
        
        owner = create_user(username=f"owner_mod_{uid}", email=f"owner_mod_{uid}@test.com")
        reviewer = create_user(username=f"reviewer_{uid}", email=f"reviewer_{uid}@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        review = Review(contact_id=contact.id, user_id=reviewer.id, rating=5, comment="Great!")
        db_session.add(review)
        db_session.commit()
        db_session.refresh(review)

        token = create_token(mod_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post(f"/api/admin/reviews/{review.id}/approve", headers=headers)
        assert resp.status_code == 200

    def test_moderator_cannot_manage_users(self, client, create_user, db_session):
        """Moderator should not be able to manage users."""
        uid = uuid.uuid4().hex[:8]
        mod_user = User(
            username=f"mod2_{uid}",
            email=f"mod2_{uid}@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash=bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode(),
            role="moderator",
            is_active=True,
        )
        db_session.add(mod_user)
        db_session.commit()
        db_session.refresh(mod_user)
        
        token = create_token(mod_user.id)
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = client.get("/api/users", headers=headers)
        assert resp.status_code == 403

    def test_moderator_can_verify_contact(self, client, create_user, db_session):
        """Moderator should be able to verify contact."""
        uid = uuid.uuid4().hex[:8]
        mod_user = User(
            username=f"mod3_{uid}",
            email=f"mod3_{uid}@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash=bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode(),
            role="moderator",
            is_active=True,
        )
        db_session.add(mod_user)
        
        owner = create_user(username=f"owner_v_{uid}", email=f"owner_v_{uid}@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(mod_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post(
            f"/api/contacts/{contact.id}/verify",
            headers=headers,
            json={"is_verified": True},
        )
        assert resp.status_code == 200

    def test_moderator_can_set_verification_level(self, client, create_user, db_session):
        """Moderator should be able to set verification level."""
        uid = uuid.uuid4().hex[:8]
        mod_user = User(
            username=f"mod4_{uid}",
            email=f"mod4_{uid}@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash=bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode(),
            role="moderator",
            is_active=True,
        )
        db_session.add(mod_user)
        
        owner = create_user(username=f"owner_vl_{uid}", email=f"owner_vl_{uid}@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(mod_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.put(
            f"/api/admin/contacts/{contact.id}/verification",
            headers=headers,
            json={"verification_level": 2},
        )
        assert resp.status_code == 200


class TestUnauthorizedAccess:
    """Verify endpoints that require authentication."""

    @pytest.mark.parametrize("method,url", [
        ("POST", "/api/contacts"),
        ("GET", "/api/auth/me"),
        ("GET", "/api/notifications"),
        ("GET", "/api/contacts/pending"),
        ("POST", "/api/contacts/1/reviews"),
        ("GET", "/api/provider/dashboard"),
    ])
    def test_protected_endpoints_require_auth(self, client, method, url):
        """These endpoints should return 401 without authentication."""
        resp = getattr(client, method.lower())(url)
        assert resp.status_code == 401, f"{method} {url} should return 401, got {resp.status_code}"


class TestPublicEndpoints:
    """Verify public endpoints work without auth."""

    @pytest.mark.parametrize("method,url", [
        ("GET", "/api/contacts"),
        ("GET", "/api/categories"),
        ("GET", "/api/public/users"),
        ("GET", "/api/auth/captcha"),
        ("GET", "/health"),
    ])
    def test_public_endpoints_no_auth(self, client, method, url):
        """Public endpoints should work without authentication."""
        resp = getattr(client, method.lower())(url)
        assert resp.status_code in [200, 204, 404], f"{method} {url} returned {resp.status_code}"
