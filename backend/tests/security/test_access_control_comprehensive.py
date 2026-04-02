"""Comprehensive access control and authorization tests."""
import pytest
from app.models.contact import Contact


class TestOwnerOnlyEndpoints:
    """Verify that owner-only endpoints reject non-owners."""

    def test_non_owner_cannot_update_contact(self, client, create_user, database_session):
        owner = create_user(username="owner", email="owner@test.com")
        stranger = create_user(username="stranger", email="stranger@test.com")

        contact = Contact(name="Private Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.post("/api/auth/login", json={
            "username_or_email": "stranger",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = client.put(f"/api/contacts/{contact.id}", headers=headers, json={
            "name": "Hacked Name",
        })
        assert resp.status_code == 403

    def test_non_owner_cannot_delete_contact(self, client, create_user, database_session):
        owner = create_user(username="owner", email="owner@test.com")
        stranger = create_user(username="stranger", email="stranger@test.com")

        contact = Contact(name="Private", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.post("/api/auth/login", json={
            "username_or_email": "stranger",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = client.delete(f"/api/contacts/{contact.id}", headers=headers)
        assert resp.status_code == 403

    def test_owner_must_flag_before_delete(self, client, auth_headers, contact_factory):
        headers = auth_headers()
        contact_id = contact_factory(headers)

        resp = client.delete(f"/api/contacts/{contact_id}", headers=headers)
        assert resp.status_code == 403
        assert "solicitar" in resp.json()["detail"].lower()

    def test_non_owner_cannot_request_deletion(self, client, create_user, database_session):
        owner = create_user(username="owner", email="owner@test.com")
        stranger = create_user(username="stranger", email="stranger@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.post("/api/auth/login", json={
            "username_or_email": "stranger",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = client.post(f"/api/contacts/{contact.id}/request-deletion", headers=headers)
        assert resp.status_code == 403

    def test_non_owner_cannot_upload_photo(self, client, create_user, database_session):
        owner = create_user(username="owner", email="owner@test.com")
        stranger = create_user(username="stranger", email="stranger@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.post("/api/auth/login", json={
            "username_or_email": "stranger",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        import io
        fake_jpeg = b'\xFF\xD8\xFF\xE0' + b'\x00' * 100
        resp = client.post(
            f"/api/contacts/{contact.id}/photos",
            headers=headers,
            files={"file": ("test.jpg", io.BytesIO(fake_jpeg), "image/jpeg")},
        )
        assert resp.status_code == 403

    def test_non_owner_cannot_update_schedule(self, client, create_user, database_session):
        owner = create_user(username="owner", email="owner@test.com")
        stranger = create_user(username="stranger", email="stranger@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.post("/api/auth/login", json={
            "username_or_email": "stranger",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = client.put(
            f"/api/contacts/{contact.id}/schedules",
            headers=headers,
            json=[{"day_of_week": 0, "open_time": "08:00", "close_time": "18:00"}],
        )
        assert resp.status_code == 403


class TestModeratorPermissions:
    """Verify moderator permission boundaries."""

    def test_moderator_can_approve_reviews(self, client, moderator_user, create_user, database_session):
        from app.models.review import Review
        _, mod_headers = moderator_user
        owner = create_user(username="owner", email="owner@test.com")
        reviewer = create_user(username="reviewer", email="reviewer@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        review = Review(contact_id=contact.id, user_id=reviewer.id, rating=5, comment="Great!")
        database_session.add(review)
        database_session.commit()
        database_session.refresh(review)

        resp = client.post(f"/api/admin/reviews/{review.id}/approve", headers=mod_headers)
        assert resp.status_code == 200

    def test_moderator_cannot_manage_users(self, client, moderator_user):
        _, headers = moderator_user
        resp = client.get("/api/users", headers=headers)
        assert resp.status_code == 403

    def test_moderator_can_verify_contact(self, client, moderator_user, create_user, database_session):
        _, mod_headers = moderator_user
        owner = create_user(username="owner", email="owner@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.post(
            f"/api/contacts/{contact.id}/verify",
            headers=mod_headers,
            json={"is_verified": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_verified"] is True

    def test_moderator_can_set_verification_level(self, client, moderator_user, create_user, database_session):
        _, mod_headers = moderator_user
        owner = create_user(username="owner", email="owner@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        resp = client.put(
            f"/api/admin/contacts/{contact.id}/verification",
            headers=mod_headers,
            json={"verification_level": 2},
        )
        assert resp.status_code == 200
        assert resp.json()["verification_level"] == 2


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
        ("GET", "/api/users/active"),
        ("GET", "/api/auth/captcha"),
        ("GET", "/health"),
    ])
    def test_public_endpoints_no_auth(self, client, method, url):
        """These endpoints should work without authentication."""
        resp = getattr(client, method.lower())(url)
        assert resp.status_code == 200, f"{method} {url} should return 200, got {resp.status_code}"
