"""Integration tests for authentication endpoints.

Covers:
- Registration (happy path, duplicates, validation)
- Login (email/username, wrong password, inactive users)
- Token validation and protected endpoints
- First-user-is-admin bootstrap
"""
import pytest


class TestRegistro:

    @pytest.mark.integration
    def test_registro_exitoso(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "nuevo",
            "email": "nuevo@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
        })
        assert resp.status_code in [200, 201]
        data = resp.json()
        assert "token" in data
        assert data["user"]["username"] == "nuevo"
        assert data["user"]["role"] == "user"
        assert data["user"]["is_active"] is True

    @pytest.mark.integration
    def test_registro_siempre_crea_user(self, client):
        """Register always creates 'user' role, never 'admin'."""
        resp = client.post("/api/auth/register", json={
            "username": "regular",
            "email": "regular@test.com",
            "phone_area_code": "0341",
            "phone_number": "1111111",
            "password": "password123",
        })
        assert resp.status_code == 201
        assert resp.json()["user"]["role"] == "user"

    @pytest.mark.integration
    def test_bootstrap_admin_crea_primer_admin(self, client):
        """Bootstrap-admin creates the first admin when DB is empty."""
        resp = client.post("/api/auth/bootstrap-admin", json={
            "username": "superadmin",
            "email": "admin@test.com",
            "phone_area_code": "0341",
            "phone_number": "9999999",
            "password": "adminpass123",
        })
        assert resp.status_code == 201
        assert resp.json()["user"]["role"] == "admin"

    @pytest.mark.integration
    def test_bootstrap_admin_rechazado_si_hay_usuarios(self, client):
        """Bootstrap-admin fails if there are already users."""
        client.post("/api/auth/register", json={
            "username": "existing",
            "email": "exist@test.com",
            "phone_area_code": "0341",
            "phone_number": "1111111",
            "password": "password123",
        })
        resp = client.post("/api/auth/bootstrap-admin", json={
            "username": "anotheradmin",
            "email": "admin2@test.com",
            "phone_area_code": "0341",
            "phone_number": "2222222",
            "password": "adminpass123",
        })
        assert resp.status_code == 403

    @pytest.mark.integration
    def test_registro_email_duplicado(self, client):
        client.post("/api/auth/register", json={
            "username": "user1",
            "email": "dup@test.com",
            "phone_area_code": "0341",
            "phone_number": "1111111",
            "password": "password123",
        })
        resp = client.post("/api/auth/register", json={
            "username": "user2",
            "email": "dup@test.com",
            "phone_area_code": "0341",
            "phone_number": "2222222",
            "password": "password123",
        })
        assert resp.status_code == 400

    @pytest.mark.integration
    def test_registro_username_duplicado(self, client):
        client.post("/api/auth/register", json={
            "username": "mismo",
            "email": "a@test.com",
            "phone_area_code": "0341",
            "phone_number": "1111111",
            "password": "password123",
        })
        resp = client.post("/api/auth/register", json={
            "username": "mismo",
            "email": "b@test.com",
            "phone_area_code": "0341",
            "phone_number": "2222222",
            "password": "password123",
        })
        assert resp.status_code == 400

    @pytest.mark.integration
    def test_registro_campos_invalidos(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "ab",
            "email": "test@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
        })
        assert resp.status_code == 422

    @pytest.mark.integration
    def test_registro_password_muy_corto(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "validuser",
            "email": "short@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "short",
        })
        assert resp.status_code == 422

    @pytest.mark.integration
    def test_registro_email_invalido(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "validuser",
            "email": "notanemail",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
        })
        assert resp.status_code == 422

    @pytest.mark.integration
    def test_registro_body_vacio(self, client):
        resp = client.post("/api/auth/register", json={})
        assert resp.status_code == 422


class TestLogin:

    @pytest.fixture(autouse=True)
    def setup_user(self, client):
        client.post("/api/auth/register", json={
            "username": "loginuser",
            "email": "login@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "correctpass",
        })

    @pytest.mark.integration
    def test_login_con_email(self, client):
        resp = client.post("/api/auth/login", json={
            "username_or_email": "login@test.com",
            "password": "correctpass",
        })
        assert resp.status_code == 200
        assert "token" in resp.json()

    @pytest.mark.integration
    def test_login_con_username(self, client):
        resp = client.post("/api/auth/login", json={
            "username_or_email": "loginuser",
            "password": "correctpass",
        })
        assert resp.status_code == 200

    @pytest.mark.integration
    def test_login_contrasena_incorrecta(self, client):
        resp = client.post("/api/auth/login", json={
            "username_or_email": "loginuser",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    @pytest.mark.integration
    def test_login_usuario_inexistente(self, client):
        resp = client.post("/api/auth/login", json={
            "username_or_email": "noexiste@test.com",
            "password": "password123",
        })
        assert resp.status_code == 401

    @pytest.mark.integration
    def test_login_usuario_inactivo(self, client, create_user, database_session):
        create_user(username="inactive", email="inactive@test.com", is_active=False)
        database_session.commit()
        resp = client.post("/api/auth/login", json={
            "username_or_email": "inactive",
            "password": "password123",
        })
        assert resp.status_code == 401

    @pytest.mark.integration
    def test_login_usuario_inactivo_verificado_en_db(self, client, create_user, database_session):
        """Verify that inactive user login returns correct error and user stays inactive."""
        user = create_user(username="inactcheck", email="inactcheck@test.com", is_active=False)
        database_session.commit()

        resp = client.post("/api/auth/login", json={
            "username_or_email": "inactcheck",
            "password": "password123",
        })
        assert resp.status_code == 401
        assert "inactivo" in resp.json()["detail"].lower()

        database_session.refresh(user)
        assert user.is_active is False

    @pytest.mark.integration
    def test_login_respuesta_contiene_user_data(self, client):
        resp = client.post("/api/auth/login", json={
            "username_or_email": "loginuser",
            "password": "correctpass",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "user" in data
        assert "id" in data["user"]
        assert "username" in data["user"]
        assert "role" in data["user"]


class TestTokenJWT:

    @pytest.mark.integration
    def test_endpoint_protegido_sin_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    @pytest.mark.integration
    def test_endpoint_protegido_con_token_valido(self, client, auth_headers):
        headers = auth_headers()
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.integration
    def test_token_invalido(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer token_invalido"})
        assert resp.status_code == 401

    @pytest.mark.integration
    def test_esquema_no_bearer(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Basic abc123"})
        assert resp.status_code == 401

    @pytest.mark.integration
    def test_auth_header_vacio(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": ""})
        assert resp.status_code == 401

    @pytest.mark.integration
    def test_auth_header_solo_bearer(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer"})
        assert resp.status_code == 401

    @pytest.mark.integration
    def test_me_returns_correct_user(self, client, auth_headers):
        h = auth_headers(username="mecheck", email="mecheck@test.com")
        resp = client.get("/api/auth/me", headers=h)
        assert resp.status_code == 200
        assert resp.json()["username"] == "mecheck"
        assert resp.json()["email"] == "mecheck@test.com"
