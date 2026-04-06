"""Integration tests — Contacts CRUD + search + geo + export."""
import pytest
from tests.conftest import _bearer, api_create_contact


class TestListContacts:
    def test_list_empty(self, client):
        r = client.get("/api/contacts")
        assert r.status_code == 200
        assert "contacts" in r.json()

    def test_list_with_category_filter(self, client, create_contact):
        c = create_contact(category_id=1)
        r = client.get("/api/contacts", params={"category_id": c.category_id})
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_list_pagination(self, client, create_contact):
        for i in range(5):
            create_contact(name=f"Pag{i}")
        r = client.get("/api/contacts", params={"skip": 0, "limit": 2})
        assert r.status_code == 200
        assert len(r.json()["contacts"]) <= 2

    def test_list_excludes_suspended(self, client, create_contact):
        create_contact(status="suspended", name="Hidden")
        r = client.get("/api/contacts")
        names = [c["name"] for c in r.json()["contacts"]]
        assert "Hidden" not in names


class TestGetContact:
    def test_get_existing(self, client, create_contact):
        c = create_contact()
        r = client.get(f"/api/contacts/{c.id}")
        assert r.status_code == 200
        assert r.json()["name"] == c.name

    def test_get_nonexistent(self, client):
        r = client.get("/api/contacts/99999")
        assert r.status_code == 404


class TestCreateContact:
    def test_create_success(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers, json={
            "name": "Mi Negocio", "phone": "1234567",
        })
        assert r.status_code == 201
        assert r.json()["name"] == "Mi Negocio"

    def test_create_with_all_fields(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers, json={
            "name": "Full Contact", "phone": "1234567",
            "email": "full@test.com", "address": "Calle 1",
            "city": "Rosario", "neighborhood": "Centro",
            "description": "Desc", "latitude": -32.9,
            "longitude": -60.6, "website": "https://example.com",
            "instagram": "@test", "facebook": "https://fb.com/test",
            "about": "Long description here",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["city"] == "Rosario"
        assert data["latitude"] == -32.9

    def test_create_unauthenticated(self, client):
        r = client.post("/api/contacts", json={"name": "X", "phone": "123"})
        assert r.status_code == 401

    def test_create_name_too_short(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers, json={
            "name": "X",
        })
        assert r.status_code == 422

    def test_create_assigns_user_id(self, client, create_user):
        user = create_user()
        headers = _bearer(user)
        r = client.post("/api/contacts", headers=headers, json={
            "name": "Owned Contact", "phone": "1234567",
        })
        assert r.status_code == 201
        assert r.json()["user_id"] == user.id


class TestUpdateContact:
    def test_update_by_owner(self, client, create_user, create_contact):
        user = create_user()
        c = create_contact(user_id=user.id)
        r = client.put(f"/api/contacts/{c.id}", headers=_bearer(user), json={
            "name": "Updated Name",
        })
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Name"

    def test_update_by_non_owner(self, client, create_user, create_contact):
        owner = create_user()
        stranger = create_user()
        c = create_contact(user_id=owner.id)
        r = client.put(f"/api/contacts/{c.id}", headers=_bearer(stranger), json={
            "name": "Hacked",
        })
        assert r.status_code == 403

    def test_update_by_admin(self, client, admin_headers, create_contact):
        c = create_contact()
        r = client.put(f"/api/contacts/{c.id}", headers=admin_headers, json={
            "name": "Admin Updated",
        })
        assert r.status_code == 200

    def test_update_nonexistent(self, client, user_headers):
        r = client.put("/api/contacts/99999", headers=user_headers, json={
            "name": "Updated Name",
        })
        assert r.status_code in (404, 422)

    def test_update_tracks_history(self, client, create_user, db_session, create_contact):
        from app.models.contact import ContactHistory
        user = create_user()
        c = create_contact(user_id=user.id, name="Original")
        client.put(f"/api/contacts/{c.id}", headers=_bearer(user), json={
            "name": "Changed",
        })
        hist = db_session.query(ContactHistory).filter(
            ContactHistory.contact_id == c.id,
        ).all()
        assert len(hist) >= 1
        assert any(h.field_name == "name" for h in hist)


class TestDeleteContact:
    def test_delete_by_admin(self, client, admin_headers, create_contact):
        c = create_contact()
        r = client.delete(f"/api/contacts/{c.id}", headers=admin_headers)
        assert r.status_code == 204

    def test_delete_by_owner_not_flagged(self, client, create_user, create_contact):
        user = create_user()
        c = create_contact(user_id=user.id, status="active")
        r = client.delete(f"/api/contacts/{c.id}", headers=_bearer(user))
        assert r.status_code == 403

    def test_delete_by_owner_flagged(self, client, create_user, create_contact):
        user = create_user()
        c = create_contact(user_id=user.id, status="flagged")
        r = client.delete(f"/api/contacts/{c.id}", headers=_bearer(user))
        assert r.status_code == 204

    def test_delete_nonexistent(self, client, admin_headers):
        r = client.delete("/api/contacts/99999", headers=admin_headers)
        assert r.status_code == 404


class TestSearchContacts:
    def test_search_by_text(self, client, create_contact):
        create_contact(name="Plomeria Juan", city="Rosario")
        r = client.get("/api/contacts/search", params={"q": "Juan"})
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_search_by_category(self, client, create_contact):
        c = create_contact()
        r = client.get("/api/contacts/search", params={"category_id": c.category_id})
        assert r.status_code == 200

    def test_search_requires_filter(self, client):
        r = client.get("/api/contacts/search")
        assert r.status_code == 400

    def test_search_by_geo(self, client, create_contact):
        create_contact(latitude=-32.9, longitude=-60.6)
        r = client.get("/api/contacts/search", params={
            "lat": -32.9, "lon": -60.6, "radius_km": 10,
        })
        assert r.status_code == 200

    def test_search_invalid_coords(self, client):
        r = client.get("/api/contacts/search", params={
            "lat": 999, "lon": 999, "radius_km": 10,
        })
        assert r.status_code == 400

    def test_search_geo_includes_distance(self, client, create_contact):
        create_contact(latitude=-32.9, longitude=-60.6)
        r = client.get("/api/contacts/search", params={
            "lat": -32.9, "lon": -60.6, "radius_km": 10,
        })
        if r.json()["contacts"]:
            assert "distance_km" in r.json()["contacts"][0]

    def test_search_phone(self, client, create_contact):
        create_contact(phone="341-555-1234")
        r = client.get("/api/contacts/search/phone", params={"phone": "555"})
        assert r.status_code == 200


class TestExportContacts:
    def test_export_csv_by_admin(self, client, admin_headers, create_contact):
        create_contact()
        r = client.get("/api/contacts/export", headers=admin_headers,
                        params={"format": "csv"})
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "name" in r.text

    def test_export_json_by_admin(self, client, admin_headers, create_contact):
        create_contact()
        r = client.get("/api/contacts/export", headers=admin_headers,
                        params={"format": "json"})
        assert r.status_code == 200

    def test_export_forbidden_for_regular_user(self, client, user_headers):
        r = client.get("/api/contacts/export", headers=user_headers)
        assert r.status_code == 403

    def test_export_unauthenticated(self, client):
        r = client.get("/api/contacts/export")
        assert r.status_code == 401


class TestVerifyContact:
    def test_verify_by_owner(self, client, create_user, create_contact):
        user = create_user()
        c = create_contact(user_id=user.id)
        r = client.post(f"/api/contacts/{c.id}/verify", headers=_bearer(user),
                         json={"is_verified": True})
        assert r.status_code == 200
        assert r.json()["is_verified"] is True

    def test_unverify(self, client, create_user, create_contact):
        user = create_user()
        c = create_contact(user_id=user.id)
        client.post(f"/api/contacts/{c.id}/verify", headers=_bearer(user),
                     json={"is_verified": True})
        r = client.post(f"/api/contacts/{c.id}/verify", headers=_bearer(user),
                         json={"is_verified": False})
        assert r.json()["verification_level"] == 0


class TestDeletionFlow:
    def test_request_deletion(self, client, create_user, create_contact):
        user = create_user()
        c = create_contact(user_id=user.id)
        r = client.post(f"/api/contacts/{c.id}/request-deletion",
                         headers=_bearer(user))
        assert r.status_code == 200
        assert r.json()["status"] == "flagged"

    def test_cancel_deletion(self, client, create_user, create_contact):
        user = create_user()
        c = create_contact(user_id=user.id, status="flagged")
        r = client.post(f"/api/contacts/{c.id}/cancel-deletion",
                         headers=_bearer(user))
        assert r.status_code == 200
        assert r.json()["status"] == "active"

    def test_request_deletion_already_flagged(self, client, create_user, create_contact):
        user = create_user()
        c = create_contact(user_id=user.id, status="flagged")
        r = client.post(f"/api/contacts/{c.id}/request-deletion",
                         headers=_bearer(user))
        assert r.status_code == 400

    def test_cancel_not_flagged(self, client, create_user, create_contact):
        user = create_user()
        c = create_contact(user_id=user.id, status="active")
        r = client.post(f"/api/contacts/{c.id}/cancel-deletion",
                         headers=_bearer(user))
        assert r.status_code == 400

    def test_request_deletion_not_owner(self, client, create_user, create_contact):
        c = create_contact()
        stranger = create_user()
        r = client.post(f"/api/contacts/{c.id}/request-deletion",
                         headers=_bearer(stranger))
        assert r.status_code == 403


class TestTransferOwnership:
    def test_transfer_by_owner(self, client, create_user, create_contact):
        owner = create_user()
        new_owner = create_user()
        c = create_contact(user_id=owner.id)
        r = client.put(f"/api/contacts/{c.id}/transfer-ownership",
                        headers=_bearer(owner),
                        json={"new_owner_id": new_owner.id})
        assert r.status_code == 200
        assert r.json()["user_id"] == new_owner.id

    def test_transfer_to_self(self, client, create_user, create_contact):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        r = client.put(f"/api/contacts/{c.id}/transfer-ownership",
                        headers=_bearer(owner),
                        json={"new_owner_id": owner.id})
        assert r.status_code == 400

    def test_transfer_nonexistent_new_owner(self, client, create_user, create_contact):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        r = client.put(f"/api/contacts/{c.id}/transfer-ownership",
                        headers=_bearer(owner),
                        json={"new_owner_id": 99999})
        assert r.status_code == 404

    def test_transfer_by_stranger(self, client, create_user, create_contact):
        c = create_contact()
        stranger = create_user()
        new_owner = create_user()
        r = client.put(f"/api/contacts/{c.id}/transfer-ownership",
                        headers=_bearer(stranger),
                        json={"new_owner_id": new_owner.id})
        assert r.status_code == 403

    def test_transfer_resets_flagged_status(self, client, create_user, create_contact):
        owner = create_user()
        new_owner = create_user()
        c = create_contact(user_id=owner.id, status="flagged")
        r = client.put(f"/api/contacts/{c.id}/transfer-ownership",
                        headers=_bearer(owner),
                        json={"new_owner_id": new_owner.id})
        assert r.json()["status"] == "active"


class TestLeads:
    def test_register_lead(self, client, create_contact):
        c = create_contact()
        r = client.post(f"/api/contacts/{c.id}/leads")
        assert r.status_code == 201

    def test_register_lead_nonexistent(self, client):
        r = client.post("/api/contacts/99999/leads")
        assert r.status_code == 404

    def test_get_leads_by_owner(self, client, create_user, create_contact):
        user = create_user()
        c = create_contact(user_id=user.id)
        client.post(f"/api/contacts/{c.id}/leads")
        r = client.get(f"/api/contacts/{c.id}/leads", headers=_bearer(user))
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_get_leads_forbidden(self, client, create_user, create_contact):
        c = create_contact()
        stranger = create_user()
        r = client.get(f"/api/contacts/{c.id}/leads", headers=_bearer(stranger))
        assert r.status_code == 403


class TestRelatedBusinesses:
    def test_related_with_geo(self, client, create_user, create_contact):
        user = create_user()
        cat = 1  # First category
        c1 = create_contact(user_id=user.id, category_id=cat,
                             latitude=-32.9, longitude=-60.6)
        create_contact(category_id=cat, latitude=-32.91, longitude=-60.61)
        r = client.get(f"/api/contacts/{c1.id}/related")
        assert r.status_code == 200

    def test_related_no_geo(self, client, create_contact):
        c = create_contact()  # No lat/lon
        r = client.get(f"/api/contacts/{c.id}/related")
        assert r.status_code == 200
        assert r.json() == []


class TestSchedules:
    def test_list_schedules(self, client, create_contact):
        c = create_contact()
        r = client.get(f"/api/contacts/{c.id}/schedules")
        assert r.status_code == 200

    def test_update_schedules(self, client, create_user, create_contact):
        user = create_user()
        c = create_contact(user_id=user.id)
        r = client.put(f"/api/contacts/{c.id}/schedules",
                        headers=_bearer(user), json=[
            {"day_of_week": 0, "open_time": "08:00", "close_time": "18:00"},
            {"day_of_week": 5, "open_time": None, "close_time": None},
        ])
        assert r.status_code == 200

    def test_update_schedules_forbidden(self, client, create_user, create_contact):
        c = create_contact()
        stranger = create_user()
        r = client.put(f"/api/contacts/{c.id}/schedules",
                        headers=_bearer(stranger), json=[])
        assert r.status_code == 403


class TestPendingContacts:
    def test_list_pending_by_owner(self, client, create_user, create_contact, db_session):
        user = create_user()
        c = create_contact(user_id=user.id)
        c.pending_changes_count = 1
        db_session.commit()
        r = client.get("/api/contacts/pending", headers=_bearer(user))
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_list_pending_unauthenticated(self, client):
        r = client.get("/api/contacts/pending")
        assert r.status_code == 401
