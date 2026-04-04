"""Integration tests for utilities API — admin CRUD and public listing."""
import pytest


class TestUtilitiesCRUD:
    """Admin create/update/soft-delete utility items."""

    @pytest.fixture(autouse=True)
    def setup(self, client, moderator_user):
        self.mod_user, self.mod_headers = moderator_user

    def test_admin_create_utility(self, client):
        resp = client.post("/api/admin/utilities",
            headers=self.mod_headers,
            json={
                "type": "farmacia_turno",
                "name": "Farmacia del Pueblo",
                "phone": "3411234567",
                "address": "San Martin 1234",
                "schedule": "Lun-Dom 8-22",
                "city": "Rosario",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Farmacia del Pueblo"
        assert data["type"] == "farmacia_turno"
        assert data["is_active"] is True

    def test_admin_update_utility(self, client):
        create_resp = client.post("/api/admin/utilities",
            headers=self.mod_headers,
            json={"name": "Old Name", "type": "otro"},
        )
        item_id = create_resp.json()["id"]

        resp = client.put(f"/api/admin/utilities/{item_id}",
            headers=self.mod_headers,
            json={"name": "New Name", "phone": "3419999999"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"
        assert resp.json()["phone"] == "3419999999"

    def test_admin_soft_delete_utility(self, client):
        create_resp = client.post("/api/admin/utilities",
            headers=self.mod_headers,
            json={"name": "To Delete", "type": "otro"},
        )
        item_id = create_resp.json()["id"]

        resp = client.delete(f"/api/admin/utilities/{item_id}",
            headers=self.mod_headers,
        )
        assert resp.status_code == 204

        # Should not appear in public list
        resp = client.get("/api/utilities")
        assert resp.status_code == 200
        items = resp.json()
        assert not any(i["id"] == item_id for i in items)


class TestUtilitiesPublicAccess:
    """Public listing of utilities with type filter."""

    def test_public_list_utilities(self, client, moderator_user):
        _, mod_headers = moderator_user
        client.post("/api/admin/utilities", headers=mod_headers,
            json={"name": "Public Item", "type": "emergencia"})

        resp = client.get("/api/utilities")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_public_filter_by_type(self, client, moderator_user):
        _, mod_headers = moderator_user
        client.post("/api/admin/utilities", headers=mod_headers,
            json={"name": "Farmacia", "type": "farmacia_turno"})
        client.post("/api/admin/utilities", headers=mod_headers,
            json={"name": "Hospital", "type": "emergencia"})

        resp = client.get("/api/utilities", params={"type": "farmacia_turno"})
        assert resp.status_code == 200
        items = resp.json()
        assert all(i["type"] == "farmacia_turno" for i in items)

    def test_non_admin_cannot_create_utility(self, client, auth_headers):
        headers = auth_headers(username="utl_stranger", email="utlstranger@test.com")
        resp = client.post("/api/admin/utilities",
            headers=headers,
            json={"name": "Hack", "type": "otro"},
        )
        assert resp.status_code == 403

    def test_non_admin_cannot_delete_utility(self, client, moderator_user, auth_headers):
        _, mod_headers = moderator_user
        user_headers = auth_headers(username="utl_stranger2", email="utlstranger2@test.com")

        create_resp = client.post("/api/admin/utilities",
            headers=mod_headers, json={"name": "Protected", "type": "otro"})
        item_id = create_resp.json()["id"]

        resp = client.delete(f"/api/admin/utilities/{item_id}", headers=user_headers)
        assert resp.status_code == 403
