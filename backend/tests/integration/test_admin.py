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
