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
        assert data["user"]["role"] in ["user", "admin"]
        assert data["user"]["is_active"] is True

    @pytest.mark.integration
    def test_registro_primer_usuario_es_admin(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "primeradmin",
            "email": "first@test.com",
            "phone_area_code": "0341",
            "phone_number": "1111111",
            "password": "password123",
        })
        assert resp.status_code in [200, 201]
        assert resp.json()["user"]["role"] == "admin"

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
    def test_login_usuario_inactivo(self, client, create_user, db_session):
        create_user(username="inactive", email="inactive@test.com", is_active=False)
        db_session.commit()
        resp = client.post("/api/auth/login", json={
            "username_or_email": "inactive",
            "password": "password123",
        })
        assert resp.status_code == 401


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
