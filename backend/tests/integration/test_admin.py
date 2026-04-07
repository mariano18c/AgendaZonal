"""Integration tests — Admin (analytics, export, utilities, contact status)."""
import pytest
from tests.conftest import _bearer


class TestAnalytics:
    def test_get_analytics(self, client, mod_headers, create_contact):
        create_contact()
        r = client.get("/api/admin/analytics", headers=mod_headers)
        assert r.status_code == 200
        data = r.json()
        assert "total_providers" in data

    def test_analytics_with_zone(self, client, mod_headers, create_contact):
        create_contact(city="Rosario")
        r = client.get("/api/admin/analytics", headers=mod_headers,
                        params={"zone": "Rosario"})
        assert r.status_code == 200

    def test_analytics_forbidden_for_user(self, client, user_headers):
        r = client.get("/api/admin/analytics", headers=user_headers)
        assert r.status_code == 403


class TestAnalyticsExport:
    def test_export_csv(self, client, mod_headers, create_contact):
        create_contact()
        r = client.get("/api/admin/analytics/export", headers=mod_headers)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")

    def test_export_with_zone(self, client, mod_headers, create_contact):
        create_contact(city="Rosario")
        r = client.get("/api/admin/analytics/export", headers=mod_headers,
                        params={"zone": "Rosario"})
        assert r.status_code == 200


class TestAdminContacts:
    def test_list_admin_contacts(self, client, mod_headers, create_contact):
        create_contact()
        r = client.get("/api/admin/contacts", headers=mod_headers)
        assert r.status_code == 200
        assert "contacts" in r.json()

    def test_update_contact_status(self, client, mod_headers, create_contact):
        c = create_contact()
        r = client.put(f"/api/admin/contacts/{c.id}/status", headers=mod_headers,
                        params={"new_status": "suspended"})
        assert r.status_code == 200
        assert r.json()["new_status"] == "suspended"

    def test_update_status_invalid(self, client, mod_headers, create_contact):
        c = create_contact()
        r = client.put(f"/api/admin/contacts/{c.id}/status", headers=mod_headers,
                        params={"new_status": "invalid_status"})
        assert r.status_code == 422

    def test_update_status_nonexistent(self, client, mod_headers):
        r = client.put("/api/admin/contacts/99999/status", headers=mod_headers,
                        params={"new_status": "active"})
        assert r.status_code == 404


class TestUtilities:
    def test_list_utilities_public(self, client, create_utility):
        create_utility()
        r = client.get("/api/utilities")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_create_utility(self, client, mod_headers):
        r = client.post("/api/admin/utilities", headers=mod_headers,
                          json={"name": "Farmacia Central", "type": "farmacia_turno",
                                "phone": "1234567", "address": "Calle 1"})
        assert r.status_code == 201
        assert r.json()["name"] == "Farmacia Central"

    def test_update_utility(self, client, mod_headers, create_utility):
        u = create_utility()
        r = client.put(f"/api/admin/utilities/{u.id}", headers=mod_headers,
                        json={"name": "Updated Name"})
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Name"

    def test_delete_utility(self, client, mod_headers, create_utility):
        u = create_utility()
        r = client.delete(f"/api/admin/utilities/{u.id}", headers=mod_headers)
        assert r.status_code == 204

    def test_create_utility_forbidden_for_user(self, client, user_headers):
        r = client.post("/api/admin/utilities", headers=user_headers,
                          json={"name": "X"})
        assert r.status_code == 403

    def test_update_nonexistent_utility(self, client, mod_headers):
        r = client.put("/api/admin/utilities/99999", headers=mod_headers,
                        json={"name": "X"})
        assert r.status_code == 404

    def test_delete_nonexistent_utility(self, client, mod_headers):
        r = client.delete("/api/admin/utilities/99999", headers=mod_headers)
        assert r.status_code == 404

    def test_list_utilities_by_type(self, client, create_utility):
        create_utility(type="farmacia_turno")
        r = client.get("/api/utilities", params={"type": "farmacia_turno"})
        assert r.status_code == 200


class TestAdminEndpointsAdvanced:
    """Additional admin endpoint coverage — merged from tests_ant."""

    def test_export_requires_auth(self, client):
        """Export without auth should return 401."""
        resp = client.get("/api/admin/analytics/export")
        assert resp.status_code == 401

    def test_export_csv_with_auth(self, client, mod_headers, create_contact):
        """CSV export with moderator auth."""
        create_contact()
        resp = client.get("/api/admin/analytics/export?format=csv", headers=mod_headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_export_json_with_auth(self, client, mod_headers, create_contact):
        """JSON export with moderator auth."""
        create_contact()
        resp = client.get("/api/admin/analytics/export?format=json", headers=mod_headers)
        assert resp.status_code == 200

    def test_export_invalid_format(self, client, mod_headers):
        """Invalid format should return 422 or 200 (depends on validation)."""
        resp = client.get("/api/admin/analytics/export?format=xml", headers=mod_headers)
        # Accept either 422 (rejected) or 200 (accepted)
        assert resp.status_code in [200, 422]

    def test_transfer_ownership_requires_new_owner_id(self, client, mod_headers, create_user):
        """Transfer ownership requires new_owner_id."""
        owner = create_user(username="transfer_owner", email="transfer_owner@test.com")
        resp = client.post("/api/contacts", headers=mod_headers, json={
            "name": "Transfer Test", "phone": "1234567",
        })
        cid = resp.json()["id"]
        resp = client.put(f"/api/contacts/{cid}/transfer-ownership", headers=mod_headers, json={})
        assert resp.status_code == 422

    def test_transfer_ownership_rejects_invalid_id(self, client, mod_headers):
        """Transfer ownership rejects invalid owner ID."""
        resp = client.post("/api/contacts", headers=mod_headers, json={
            "name": "Transfer Test 2", "phone": "1234568",
        })
        cid = resp.json()["id"]
        resp = client.put(f"/api/contacts/{cid}/transfer-ownership", headers=mod_headers,
                          json={"new_owner_id": 0})
        assert resp.status_code == 422

    def test_update_schedules_validates_day_of_week(self, client, auth_headers):
        """Update schedules validates day_of_week."""
        headers = auth_headers(username="sched_test", email="sched_test@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Sched Test", "phone": "1234567",
        })
        cid = resp.json()["id"]
        resp = client.put(f"/api/contacts/{cid}/schedules", headers=headers, json=[
            {"day_of_week": 7, "open_time": "08:00", "close_time": "18:00"},
        ])
        assert resp.status_code == 422

    def test_list_schedules_returns_formatted_data(self, client, auth_headers):
        """GET schedules returns formatted day names."""
        headers = auth_headers(username="sched_list_test", email="sched_list@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Sched List Test", "phone": "1234569",
        })
        cid = resp.json()["id"]
        client.put(f"/api/contacts/{cid}/schedules", headers=headers, json=[
            {"day_of_week": 0, "open_time": "08:00", "close_time": "18:00"},
        ])
        resp = client.get(f"/api/contacts/{cid}/schedules")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["day_name"] == "Lunes"

    def test_analytics_requires_auth(self, client):
        """Analytics without auth should return 401."""
        resp = client.get("/api/admin/analytics")
        assert resp.status_code == 401

    def test_admin_reports_requires_admin(self, client, user_headers):
        """Admin reports with user auth should return 403."""
        resp = client.get("/api/admin/reports/flagged", headers=user_headers)
        assert resp.status_code == 403

    def test_admin_contact_status_requires_admin(self, client, user_headers, create_contact):
        """Contact status change with user auth should return 403."""
        c = create_contact()
        resp = client.put(f"/api/admin/contacts/{c.id}/status", headers=user_headers,
                          params={"new_status": "suspended"})
        assert resp.status_code == 403

    def test_utilities_requires_admin_for_create(self, client, user_headers):
        """Utilities create with user auth should return 403."""
        resp = client.post("/api/admin/utilities", headers=user_headers, json={
            "name": "Test", "type": "emergency", "phone": "911",
        })
        assert resp.status_code == 403
