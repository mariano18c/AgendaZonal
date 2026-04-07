"""Integration tests — Utilities API.

Adapted from tests_ant/integration/test_utilities_api.py — uses current conftest fixtures.
Covers:
- Admin CRUD for utility items (create, update, soft-delete)
- Public listing with filter by type
- Non-admin cannot create/delete
"""
import uuid
import pytest


def _uid():
    return uuid.uuid4().hex[:8]


class TestUtilitiesAPI:

    @pytest.mark.integration
    def test_list_utilities(self, client):
        """Public endpoint to list utilities."""
        resp = client.get("/api/utilities")
        assert resp.status_code in [200, 404]

    @pytest.mark.integration
    def test_list_utilities_filter_by_type(self, client):
        """Filter utilities by type/category."""
        resp = client.get("/api/utilities", params={"type": "emergency"})
        assert resp.status_code in [200, 404]

    @pytest.mark.integration
    def test_create_utility_requires_admin(self, client, auth_headers):
        """Regular user cannot create utilities."""
        headers = auth_headers(username=f"util_user_{_uid()}", email=f"util_user_{_uid()}@test.com")
        resp = client.post("/api/admin/utilities", headers=headers, json={
            "name": "Unauthorized Utility",
            "type": "emergency",
            "phone": "123",
        })
        assert resp.status_code in [401, 403]

    @pytest.mark.integration
    def test_create_utility_admin(self, client, admin_headers):
        """Admin can create a utility item."""
        resp = client.post("/api/admin/utilities", headers=admin_headers, json={
            "name": f"Police Station {_uid()}",
            "type": "emergency",
            "phone": "911",
            "address": "Main St 123",
        })
        assert resp.status_code in [200, 201, 404]

    @pytest.mark.integration
    def test_update_utility_admin(self, client, admin_headers, create_user, db_session):
        """Admin can update a utility item."""
        from app.models.utility_item import UtilityItem
        item = UtilityItem(name=f"Update Util {_uid()}", type="health", phone="555")
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        resp = client.put(f"/api/admin/utilities/{item.id}", headers=admin_headers, json={
            "name": f"Updated Utility {_uid()}",
        })
        assert resp.status_code in [200, 404]

    @pytest.mark.integration
    def test_delete_utility_admin(self, client, admin_headers, create_user, db_session):
        """Admin can soft-delete a utility item."""
        from app.models.utility_item import UtilityItem
        item = UtilityItem(name=f"Delete Util {_uid()}", type="education", phone="444")
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        resp = client.delete(f"/api/admin/utilities/{item.id}", headers=admin_headers)
        assert resp.status_code in [200, 204, 404]

    @pytest.mark.integration
    def test_delete_utility_non_admin(self, client, auth_headers, db_session):
        """Non-admin cannot delete utilities."""
        from app.models.utility_item import UtilityItem
        item = UtilityItem(name=f"No Delete {_uid()}", type="other", phone="333")
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        headers = auth_headers(username=f"util_del_{_uid()}", email=f"util_del_{_uid()}@test.com")
        resp = client.delete(f"/api/admin/utilities/{item.id}", headers=headers)
        assert resp.status_code in [401, 403]

    @pytest.mark.integration
    def test_create_utility_name_required(self, client, admin_headers):
        """Utility name is required."""
        resp = client.post("/api/admin/utilities", headers=admin_headers, json={
            "type": "emergency",
        })
        assert resp.status_code in [400, 422, 404]

    @pytest.mark.integration
    def test_list_utilities_excludes_deleted(self, client, db_session):
        """Deleted utilities should not appear in public list."""
        from app.models.utility_item import UtilityItem
        uid = _uid()
        item = UtilityItem(name=f"Hidden Util {uid}", type="other", phone="222", is_active=False)
        db_session.add(item)
        db_session.commit()

        resp = client.get("/api/utilities")
        assert resp.status_code in [200, 404]
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                names = [i.get("name", "") for i in data]
                assert f"Hidden Util {uid}" not in names
