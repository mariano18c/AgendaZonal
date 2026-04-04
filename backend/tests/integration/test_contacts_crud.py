"""Integration tests — Contacts CRUD, search, geo, schedules, photos, changes."""
import pytest
from app.models.contact import Contact
from app.models.contact_change import ContactChange
from app.models.contact_history import ContactHistory


class TestContactCreate:
    """Test contact creation via API."""

    def test_create_contact_minimal(self, client, auth_headers):
        """Create contact with only required fields."""
        headers = auth_headers(username="create1", email="create1@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Mi Negocio",
            "phone": "1234567",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Mi Negocio"
        assert data["phone"] == "1234567"
        assert "id" in data

    def test_create_contact_full(self, client, auth_headers):
        """Create contact with all fields."""
        headers = auth_headers(username="create2", email="create2@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Negocio Completo",
            "phone": "(0341) 123-4567",
            "email": "negocio@test.com",
            "address": "Calle 123",
            "city": "Rosario",
            "neighborhood": "Centro",
            "description": "Descripción del negocio",
            "latitude": -32.9442,
            "longitude": -60.6505,
            "instagram": "@negocio",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["city"] == "Rosario"
        assert data["latitude"] == -32.9442

    def test_create_contact_requires_auth(self, client):
        """Unauthenticated user should get 401."""
        resp = client.post("/api/contacts", json={
            "name": "No Auth",
            "phone": "123",
        })
        assert resp.status_code == 401

    def test_create_contact_invalid_name(self, client, auth_headers):
        """Name too short should return 422."""
        headers = auth_headers(username="create3", email="create3@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "A",
            "phone": "123",
        })
        assert resp.status_code == 422

    def test_create_contact_persists_to_db(self, client, auth_headers, db_session):
        """Created contact should be queryable in DB."""
        headers = auth_headers(username="create4", email="create4@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "DB Test",
            "phone": "1234567",
        })
        assert resp.status_code == 201
        contact_id = resp.json()["id"]

        # Verify in DB
        contact = db_session.query(Contact).filter(Contact.id == contact_id).first()
        assert contact is not None
        assert contact.name == "DB Test"


class TestContactRead:
    """Test contact retrieval."""

    def test_get_contact_by_id(self, client, create_contact):
        """GET /api/contacts/{id} should return contact data."""
        contact = create_contact(name="Get Test")
        resp = client.get(f"/api/contacts/{contact.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Get Test"

    def test_get_nonexistent_contact(self, client):
        """GET /api/contacts/999999 should return 404."""
        resp = client.get("/api/contacts/999999")
        assert resp.status_code == 404

    def test_list_contacts_empty(self, client):
        """List contacts when none exist."""
        resp = client.get("/api/contacts")
        assert resp.status_code == 200

    def test_list_contacts_with_pagination(self, client, create_contact):
        """List contacts should support pagination."""
        create_contact(name="Contact 1")
        create_contact(name="Contact 2")
        create_contact(name="Contact 3")

        resp = client.get("/api/contacts?limit=2&skip=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["contacts"]) <= 2
        assert data["total"] >= 3


class TestContactUpdate:
    """Test contact update."""

    def test_update_contact_owner(self, client, auth_headers, create_contact):
        """Owner should be able to update their contact."""
        headers = auth_headers(username="update1", email="update1@test.com")
        contact = create_contact(name="Original", user_id=None)
        # Get the owner's user_id from the contact
        owner_id = contact.user_id

        # Create a user that owns the contact
        from app.auth import create_token
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        resp = client.put(f"/api/contacts/{contact.id}", headers=owner_headers, json={
            "name": "Updated Name",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    def test_update_contact_non_owner_403(self, client, auth_headers, create_contact):
        """Non-owner should get 403 on update."""
        headers = auth_headers(username="update2", email="update2@test.com")
        contact = create_contact(name="Not Yours")

        resp = client.put(f"/api/contacts/{contact.id}", headers=headers, json={
            "name": "Hacked",
        })
        assert resp.status_code == 403

    def test_update_nonexistent_contact(self, client, auth_headers):
        """Update non-existent contact should return 404."""
        headers = auth_headers(username="update3", email="update3@test.com")
        resp = client.put("/api/contacts/999999", headers=headers, json={
            "name": "Nope",
        })
        assert resp.status_code == 404


class TestContactDelete:
    """Test contact deletion."""

    def test_delete_contact_owner(self, client, db_session, auth_headers):
        """Owner should be able to delete their contact."""
        from app.auth import create_token
        headers = auth_headers(username="delete1", email="delete1@test.com")
        # Create contact via API
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Delete Me",
            "phone": "1234567",
        })
        assert create_resp.status_code == 201
        contact_id = create_resp.json()["id"]

        # Delete
        resp = client.delete(f"/api/contacts/{contact_id}", headers=headers)
        assert resp.status_code == 200

        # Verify deleted from DB
        contact = db_session.query(Contact).filter(Contact.id == contact_id).first()
        assert contact is None

    def test_delete_contact_non_owner_403(self, client, auth_headers, create_contact):
        """Non-owner should get 403 on delete."""
        headers = auth_headers(username="delete2", email="delete2@test.com")
        contact = create_contact(name="Not Yours")

        resp = client.delete(f"/api/contacts/{contact.id}", headers=headers)
        assert resp.status_code == 403


class TestContactSearch:
    """Test contact search functionality."""

    def test_search_by_name(self, client, create_contact):
        """Search should find contacts by name."""
        create_contact(name="Juan Plomero")
        create_contact(name="Maria Electricista")

        resp = client.get("/api/contacts/search?q=Juan")
        assert resp.status_code == 200
        results = resp.json()
        assert any("Juan" in r["name"] for r in results)

    def test_search_no_results(self, client):
        """Search with no matches should return empty list."""
        resp = client.get("/api/contacts/search?q=NonExistentXYZ123")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_search_empty_query(self, client):
        """Empty search query should return all or handle gracefully."""
        resp = client.get("/api/contacts/search?q=")
        assert resp.status_code == 200

    def test_search_case_insensitive(self, client, create_contact):
        """Search should be case insensitive."""
        create_contact(name="ROBERTO Carpintero")
        resp = client.get("/api/contacts/search?q=roberto")
        assert resp.status_code == 200
        results = resp.json()
        assert any("ROBERTO" in r["name"] or "Roberto" in r["name"] for r in results)


class TestContactSchedules:
    """Test schedule CRUD."""

    def test_list_schedules_empty(self, client, create_contact):
        """New contact should have empty schedules."""
        contact = create_contact(name="Schedule Test")
        resp = client.get(f"/api/contacts/{contact.id}/schedules")
        assert resp.status_code == 200

    def test_update_schedules_owner(self, client, db_session, auth_headers):
        """Owner should be able to update schedules."""
        from app.auth import create_token
        headers = auth_headers(username="sched1", email="sched1@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Schedule Biz",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        owner_id = create_resp.json()["user_id"]
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        resp = client.put(f"/api/contacts/{cid}/schedules", headers=owner_headers, json=[
            {"day_of_week": 1, "open_time": "09:00", "close_time": "18:00"},
            {"day_of_week": 2, "open_time": "09:00", "close_time": "18:00"},
        ])
        assert resp.status_code == 200

    def test_update_schedules_invalid_day(self, client, auth_headers):
        """Day of week > 6 should be rejected."""
        headers = auth_headers(username="sched2", email="sched2@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Schedule Biz 2",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        owner_id = create_resp.json()["user_id"]
        from app.auth import create_token
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        resp = client.put(f"/api/contacts/{cid}/schedules", headers=owner_headers, json=[
            {"day_of_week": 7, "open_time": "09:00", "close_time": "18:00"},
        ])
        assert resp.status_code == 422


class TestContactChanges:
    """Test pending change requests."""

    def test_request_change_non_owner(self, client, auth_headers, create_contact):
        """Non-owner should be able to suggest changes via /edit."""
        headers = auth_headers(username="change1", email="change1@test.com")
        contact = create_contact(name="Original Name")

        resp = client.put(f"/api/contacts/{contact.id}/edit", headers=headers, json={
            "description": "Suggested description",
        })
        # Should succeed as a pending change
        assert resp.status_code == 200

    def test_list_changes_owner(self, client, auth_headers, create_contact):
        """Owner should see pending changes on their contact."""
        headers = auth_headers(username="change2", email="change2@test.com")
        contact = create_contact(name="Change Test")

        # Another user suggests a change
        other_headers = auth_headers(username="change3", email="change3@test.com")
        client.put(f"/api/contacts/{contact.id}/edit", headers=other_headers, json={
            "description": "Suggested",
        })

        # Owner gets token
        from app.auth import create_token
        token = create_token(contact.user_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        resp = client.get(f"/api/contacts/{contact.id}/changes", headers=owner_headers)
        assert resp.status_code == 200

    def test_verify_change_owner(self, client, auth_headers, create_contact):
        """Owner should be able to verify a pending change."""
        headers = auth_headers(username="change4", email="change4@test.com")
        contact = create_contact(name="Verify Test")

        # Another user suggests change
        other_headers = auth_headers(username="change5", email="change5@test.com")
        client.put(f"/api/contacts/{contact.id}/edit", headers=other_headers, json={
            "description": "New description",
        })

        # Get change ID
        from app.auth import create_token
        token = create_token(contact.user_id)
        owner_headers = {"Authorization": f"Bearer {token}"}
        changes_resp = client.get(f"/api/contacts/{contact.id}/changes", headers=owner_headers)
        changes = changes_resp.json()
        assert len(changes) > 0
        change_id = changes[-1]["id"]

        # Verify
        resp = client.post(
            f"/api/contacts/{contact.id}/changes/{change_id}/verify",
            headers=owner_headers,
        )
        assert resp.status_code == 200

    def test_reject_change_owner(self, client, auth_headers, create_contact):
        """Owner should be able to reject a pending change."""
        headers = auth_headers(username="change6", email="change6@test.com")
        contact = create_contact(name="Reject Test")

        other_headers = auth_headers(username="change7", email="change7@test.com")
        client.put(f"/api/contacts/{contact.id}/edit", headers=other_headers, json={
            "description": "Bad suggestion",
        })

        from app.auth import create_token
        token = create_token(contact.user_id)
        owner_headers = {"Authorization": f"Bearer {token}"}
        changes_resp = client.get(f"/api/contacts/{contact.id}/changes", headers=owner_headers)
        change_id = changes_resp.json()[-1]["id"]

        resp = client.post(
            f"/api/contacts/{contact.id}/changes/{change_id}/reject",
            headers=owner_headers,
        )
        assert resp.status_code == 200


class TestContactHistory:
    """Test contact history tracking."""

    def test_history_created_on_update(self, client, db_session):
        """Updating a contact should create history entries."""
        from app.auth import create_token
        from tests.conftest import _hash_password
        from app.models.user import User

        user = User(
            username="hist1", email="hist1@test.com",
            phone_area_code="0341", phone_number="1234567",
            password_hash=_hash_password("password123"),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        contact = Contact(name="History Test", phone="123", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        client.put(f"/api/contacts/{contact.id}", headers=headers, json={
            "name": "Updated Name",
        })

        history = db_session.query(ContactHistory).filter(
            ContactHistory.contact_id == contact.id
        ).all()
        assert len(history) > 0
        assert any(h.field_name == "name" for h in history)


class TestPhoneSearch:
    """Test phone number search."""

    def test_search_by_phone_exact(self, client, create_contact):
        """Search by exact phone number."""
        create_contact(name="Phone Biz", phone="9876543")
        resp = client.get("/api/contacts/search/phone?phone=9876543")
        assert resp.status_code == 200
        results = resp.json()
        assert any(r["phone"] == "9876543" for r in results)

    def test_search_by_phone_partial(self, client, create_contact):
        """Search by partial phone number."""
        create_contact(name="Partial Phone", phone="5551234")
        resp = client.get("/api/contacts/search/phone?phone=555")
        assert resp.status_code == 200
        results = resp.json()
        assert any("555" in r["phone"] for r in results)

    def test_search_phone_no_results(self, client):
        """Phone search with no match."""
        resp = client.get("/api/contacts/search/phone?phone=0000000")
        assert resp.status_code == 200
        assert resp.json() == []


class TestRelatedBusinesses:
    """Test related businesses by category."""

    def test_related_by_category(self, client, create_contact, db_session):
        """Should return contacts in same category."""
        from app.models.category import Category
        cat = db_session.query(Category).first()
        c1 = create_contact(name="Related 1", category_id=cat.id)
        c2 = create_contact(name="Related 2", category_id=cat.id)

        resp = client.get(f"/api/contacts/{c1.id}/related")
        assert resp.status_code == 200
        results = resp.json()
        assert any(r["name"] == "Related 2" for r in results)


class TestGeoSearch:
    """Test geographic search."""

    def test_geo_search_finds_nearby(self, client, create_contact):
        """Search near a point should find contacts within radius."""
        create_contact(
            name="Nearby",
            latitude=-32.9442,
            longitude=-60.6505,
        )
        resp = client.get(
            "/api/contacts/search?lat=-32.9442&lon=-60.6505&radius=5"
        )
        assert resp.status_code == 200
        results = resp.json()
        assert any(r["name"] == "Nearby" for r in results)

    def test_geo_search_no_nearby(self, client, create_contact):
        """Search far from any contact should return empty."""
        create_contact(name="Far Away", latitude=-34.6037, longitude=-58.3816)
        resp = client.get(
            "/api/contacts/search?lat=-32.9442&lon=-60.6505&radius=1"
        )
        assert resp.status_code == 200
        results = resp.json()
        assert not any(r["name"] == "Far Away" for r in results)
