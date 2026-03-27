"""Integration tests covering gaps in API coverage."""
import pytest
import io
from PIL import Image


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------
class TestHealthEndpoint:

    @pytest.mark.integration
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# update_user (PUT /api/users/{user_id}) — previously 0% coverage
# ---------------------------------------------------------------------------
class TestUpdateUser:

    @pytest.mark.integration
    def test_admin_updates_user_email(self, client, admin_headers):
        create = client.post("/api/users", headers=admin_headers, json={
            "username": "updateme",
            "email": "update@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "role": "user",
        })
        uid = create.json()["id"]

        resp = client.put(f"/api/users/{uid}", headers=admin_headers, json={
            "email": "updated@test.com",
        })
        assert resp.status_code == 200
        assert resp.json()["email"] == "updated@test.com"

    @pytest.mark.integration
    def test_admin_updates_username(self, client, admin_headers):
        create = client.post("/api/users", headers=admin_headers, json={
            "username": "oldname",
            "email": "oldname@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "role": "user",
        })
        uid = create.json()["id"]

        resp = client.put(f"/api/users/{uid}", headers=admin_headers, json={
            "username": "newname",
        })
        assert resp.status_code == 200
        assert resp.json()["username"] == "newname"

    @pytest.mark.integration
    def test_update_user_duplicate_email(self, client, admin_headers):
        client.post("/api/users", headers=admin_headers, json={
            "username": "user1",
            "email": "user1@test.com",
            "phone_area_code": "0341",
            "phone_number": "1111111",
            "password": "password123",
            "role": "user",
        })
        create2 = client.post("/api/users", headers=admin_headers, json={
            "username": "user2",
            "email": "user2@test.com",
            "phone_area_code": "0341",
            "phone_number": "2222222",
            "password": "password123",
            "role": "user",
        })
        uid2 = create2.json()["id"]

        resp = client.put(f"/api/users/{uid2}", headers=admin_headers, json={
            "email": "user1@test.com",
        })
        assert resp.status_code == 400

    @pytest.mark.integration
    def test_update_user_duplicate_username(self, client, admin_headers):
        client.post("/api/users", headers=admin_headers, json={
            "username": "taken",
            "email": "taken@test.com",
            "phone_area_code": "0341",
            "phone_number": "1111111",
            "password": "password123",
            "role": "user",
        })
        create2 = client.post("/api/users", headers=admin_headers, json={
            "username": "unique",
            "email": "unique@test.com",
            "phone_area_code": "0341",
            "phone_number": "2222222",
            "password": "password123",
            "role": "user",
        })
        uid2 = create2.json()["id"]

        resp = client.put(f"/api/users/{uid2}", headers=admin_headers, json={
            "username": "taken",
        })
        assert resp.status_code == 400

    @pytest.mark.integration
    def test_update_user_not_found(self, client, admin_headers):
        resp = client.put("/api/users/99999", headers=admin_headers, json={
            "email": "ghost@test.com",
        })
        assert resp.status_code == 404

    @pytest.mark.integration
    def test_update_user_invalid_role(self, client, admin_headers):
        create = client.post("/api/users", headers=admin_headers, json={
            "username": "roletest",
            "email": "roletest@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "role": "user",
        })
        uid = create.json()["id"]

        resp = client.put(f"/api/users/{uid}", headers=admin_headers, json={
            "role": "superadmin",
        })
        assert resp.status_code == 400

    @pytest.mark.integration
    def test_update_user_password_via_admin(self, client, admin_headers):
        create = client.post("/api/users", headers=admin_headers, json={
            "username": "pwduser",
            "email": "pwduser@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "oldpassword123",
            "role": "user",
        })
        uid = create.json()["id"]

        resp = client.put(f"/api/users/{uid}", headers=admin_headers, json={
            "password": "newpassword456",
        })
        assert resp.status_code == 200

        login = client.post("/api/auth/login", json={
            "username_or_email": "pwduser",
            "password": "newpassword456",
        })
        assert login.status_code == 200

    @pytest.mark.integration
    def test_update_user_cannot_demote_admin(self, client, admin_headers):
        """Cannot change role of an admin user."""
        me = client.get("/api/auth/me", headers=admin_headers).json()
        resp = client.put(f"/api/users/{me['id']}", headers=admin_headers, json={
            "role": "user",
        })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# List users with filters
# ---------------------------------------------------------------------------
class TestListUsersFilter:

    @pytest.mark.integration
    def test_filter_active(self, client, admin_headers):
        resp = client.get("/api/users?filter=active", headers=admin_headers)
        assert resp.status_code == 200
        for u in resp.json():
            assert u["is_active"] is True

    @pytest.mark.integration
    def test_filter_inactive(self, client, admin_headers):
        # Create and deactivate a user
        create = client.post("/api/users", headers=admin_headers, json={
            "username": "inactivefilt",
            "email": "inactivefilt@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "role": "user",
        })
        uid = create.json()["id"]
        client.delete(f"/api/users/{uid}", headers=admin_headers)

        resp = client.get("/api/users?filter=inactive", headers=admin_headers)
        assert resp.status_code == 200
        assert any(u["id"] == uid for u in resp.json())


# ---------------------------------------------------------------------------
# List pending contacts
# ---------------------------------------------------------------------------
class TestListPendingContacts:

    @pytest.mark.integration
    def test_owner_sees_own_pending(self, client, auth_headers):
        h_owner = auth_headers(username="pendowner2", email="pendown2@test.com")
        h_other = auth_headers(username="pendother2", email="pendoth2@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Pending Test", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
            "description": "Cambio pendiente",
        })

        resp = client.get("/api/contacts/pending", headers=h_owner)
        assert resp.status_code == 200
        assert any(c["id"] == cid for c in resp.json())

    @pytest.mark.integration
    def test_non_owner_sees_nothing(self, client, auth_headers):
        h_owner = auth_headers(username="pendown3", email="pendown3@test.com")
        h_other = auth_headers(username="pendother3", email="pendoth3@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Not Mine", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}/edit", headers=auth_headers(username="anonsug", email="anon@test.com"), json={
            "description": "Sugerencia",
        })

        resp = client.get("/api/contacts/pending", headers=h_other)
        assert resp.status_code == 200
        assert all(c["id"] != cid for c in resp.json())


# ---------------------------------------------------------------------------
# verify_change with type conversion
# ---------------------------------------------------------------------------
class TestVerifyChangeTypeConversion:

    @pytest.mark.integration
    def test_verify_latitude_change(self, client, auth_headers):
        h_owner = auth_headers(username="latowner", email="lat@test.com")
        h_other = auth_headers(username="latother", email="latother@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Lat Test", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
            "latitude": -34.6,
        })

        changes = client.get(f"/api/contacts/{cid}/changes", headers=h_owner).json()
        change_id = changes[0]["id"]

        resp = client.post(f"/api/contacts/{cid}/changes/{change_id}/verify", headers=h_owner)
        assert resp.status_code == 200

        contact = client.get(f"/api/contacts/{cid}").json()
        assert contact["latitude"] == -34.6

    @pytest.mark.integration
    def test_verify_longitude_change(self, client, auth_headers):
        h_owner = auth_headers(username="lonowner", email="lon@test.com")
        h_other = auth_headers(username="lonother", email="lonother@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Lon Test", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
            "longitude": -58.38,
        })

        changes = client.get(f"/api/contacts/{cid}/changes", headers=h_owner).json()
        change_id = changes[0]["id"]

        resp = client.post(f"/api/contacts/{cid}/changes/{change_id}/verify", headers=h_owner)
        assert resp.status_code == 200

        contact = client.get(f"/api/contacts/{cid}").json()
        assert contact["longitude"] == -58.38

    @pytest.mark.integration
    def test_verify_category_id_change(self, client, auth_headers):
        """Verify a pending change on an empty field (description), which registered users can suggest."""
        h_owner = auth_headers(username="catowner", email="cat@test.com")
        h_other = auth_headers(username="catother", email="catother@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Cat Test", "phone": "1234567",
        })
        cid = create.json()["id"]

        # Registered non-owner can suggest to fill an empty field
        client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
            "description": "Agregado por otro usuario",
        })

        changes = client.get(f"/api/contacts/{cid}/changes", headers=h_owner).json()
        assert len(changes) >= 1
        change_id = changes[0]["id"]

        resp = client.post(f"/api/contacts/{cid}/changes/{change_id}/verify", headers=h_owner)
        assert resp.status_code == 200

        contact = client.get(f"/api/contacts/{cid}").json()
        assert contact["description"] == "Agregado por otro usuario"


# ---------------------------------------------------------------------------
# Image validation gaps
# ---------------------------------------------------------------------------
class TestImageValidation:

    def _create_jpeg_bytes(self, width=100, height=100):
        img = Image.new("RGB", (width, height), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        return buf

    @pytest.mark.integration
    def test_upload_fake_jpeg_rejected(self, client, auth_headers):
        headers = auth_headers(username="fakejpg", email="fakejpg@test.com")
        create = client.post("/api/contacts", headers=headers, json={
            "name": "Fake JPG", "phone": "1234567",
        })
        cid = create.json()["id"]

        # File with .jpg extension but non-JPEG content
        fake_content = b"This is not a JPEG file at all"
        resp = client.post(
            f"/api/contacts/{cid}/image",
            headers=headers,
            files={"file": ("fake.jpg", io.BytesIO(fake_content), "image/jpeg")},
        )
        assert resp.status_code == 400

    @pytest.mark.integration
    def test_delete_image_not_exists(self, client, auth_headers):
        headers = auth_headers(username="noimg", email="noimg@test.com")
        create = client.post("/api/contacts", headers=headers, json={
            "name": "No Image", "phone": "1234567",
        })
        cid = create.json()["id"]

        resp = client.delete(f"/api/contacts/{cid}/image", headers=headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# MAX_PENDING_CHANGES limit
# ---------------------------------------------------------------------------
class TestMaxPendingChanges:

    @pytest.mark.integration
    def test_fourth_pending_change_rejected(self, client, auth_headers):
        h_owner = auth_headers(username="maxowner", email="max@test.com")
        h_other = auth_headers(username="maxother", email="maxother@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Max Pending", "phone": "1234567",
        })
        cid = create.json()["id"]

        # Create 3 pending changes (the maximum)
        fields = ["description", "city", "address"]
        for f in fields:
            resp = client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
                f: f"Value for {f}",
            })
            assert resp.status_code == 200

        # 4th change should be rejected
        resp = client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
            "neighborhood": "Should fail",
        })
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "cambios pendientes" in detail or "maximum" in detail.lower()


# ---------------------------------------------------------------------------
# HTML page routes
# ---------------------------------------------------------------------------
class TestHTMLPages:

    @pytest.mark.integration
    def test_index_page(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    @pytest.mark.integration
    def test_search_page(self, client):
        resp = client.get("/search")
        assert resp.status_code == 200

    @pytest.mark.integration
    def test_login_page(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200

    @pytest.mark.integration
    def test_register_page(self, client):
        resp = client.get("/register")
        assert resp.status_code == 200

    @pytest.mark.integration
    def test_add_page(self, client):
        resp = client.get("/add")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/users/{user_id} as admin
# ---------------------------------------------------------------------------
class TestGetUser:

    @pytest.mark.integration
    def test_admin_gets_user(self, client, admin_headers):
        create = client.post("/api/users", headers=admin_headers, json={
            "username": "getme",
            "email": "getme@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "role": "user",
        })
        uid = create.json()["id"]

        resp = client.get(f"/api/users/{uid}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "getme"

    @pytest.mark.integration
    def test_admin_gets_nonexistent_user(self, client, admin_headers):
        resp = client.get("/api/users/99999", headers=admin_headers)
        assert resp.status_code == 404
