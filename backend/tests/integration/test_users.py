import pytest


class TestAdminUsers:

    @pytest.fixture
    def admin_setup(self, client):
        """Create admin user via bootstrap-admin endpoint"""
        resp = client.post("/api/auth/bootstrap-admin", json={
            "username": "adminmain",
            "email": "adminmain@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
        })
        token = resp.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.integration
    def test_admin_crea_usuario(self, client, admin_setup):
        resp = client.post("/api/users", headers=admin_setup, json={
            "username": "nuevouser",
            "email": "nuevo@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "role": "user",
        })
        assert resp.status_code == 201
        assert resp.json()["role"] == "user"

    @pytest.mark.integration
    def test_admin_desactiva_usuario(self, client, admin_setup):
        create = client.post("/api/users", headers=admin_setup, json={
            "username": "desactivar",
            "email": "desac@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "role": "user",
        })
        uid = create.json()["id"]

        resp = client.delete(f"/api/users/{uid}", headers=admin_setup)
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    @pytest.mark.integration
    def test_admin_reactiva_usuario(self, client, admin_setup):
        create = client.post("/api/users", headers=admin_setup, json={
            "username": "reactivar",
            "email": "react@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "role": "user",
        })
        uid = create.json()["id"]

        client.delete(f"/api/users/{uid}", headers=admin_setup)
        resp = client.post(f"/api/users/{uid}/activate", headers=admin_setup)
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    @pytest.mark.integration
    def test_admin_cambia_rol(self, client, admin_setup):
        create = client.post("/api/users", headers=admin_setup, json={
            "username": "cambiorol",
            "email": "cambio@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "role": "user",
        })
        uid = create.json()["id"]

        resp = client.put(f"/api/users/{uid}/role", headers=admin_setup, json={
            "role": "moderator",
        })
        assert resp.status_code == 200
        assert resp.json()["role"] == "moderator"

    @pytest.mark.integration
    def test_admin_reset_password(self, client, admin_setup):
        create = client.post("/api/users", headers=admin_setup, json={
            "username": "resetpwd",
            "email": "reset@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "oldpass123",
            "role": "user",
        })
        uid = create.json()["id"]

        resp = client.post(f"/api/users/{uid}/reset-password", headers=admin_setup, json={
            "new_password": "newpass456",
        })
        assert resp.status_code == 200

        login = client.post("/api/auth/login", json={
            "username_or_email": "resetpwd",
            "password": "newpass456",
        })
        assert login.status_code == 200

    @pytest.mark.integration
    def test_admin_no_cambia_propio_rol(self, client, admin_setup):
        me = client.get("/api/auth/me", headers=admin_setup).json()
        resp = client.put(
            f"/api/users/{me['id']}/role",
            headers=admin_setup,
            json={"role": "user"},
        )
        assert resp.status_code == 400

    @pytest.mark.integration
    def test_admin_no_desactiva_propia_cuenta(self, client, admin_setup):
        me = client.get("/api/auth/me", headers=admin_setup).json()
        resp = client.delete(f"/api/users/{me['id']}", headers=admin_setup)
        assert resp.status_code == 400

    @pytest.mark.integration
    def test_rol_invalido_rechazado(self, client, admin_setup):
        resp = client.post("/api/users", headers=admin_setup, json={
            "username": "invalidrole",
            "email": "inv@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "role": "superadmin",
        })
        assert resp.status_code == 400
