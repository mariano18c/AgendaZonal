import pytest


class TestCrearContacto:

    @pytest.mark.integration
    def test_crear_contacto_exitoso(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Juan Perez",
            "phone": "341-1234567",
            "email": "juan@test.com",
            "city": "Rosario",
            "category_id": 1,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Juan Perez"
        assert data["user_id"] is not None

    @pytest.mark.integration
    def test_crear_contacto_sin_autenticacion(self, client):
        resp = client.post("/api/contacts", json={
            "name": "Juan Perez",
            "phone": "341-1234567",
        })
        assert resp.status_code == 401

    @pytest.mark.integration
    def test_crear_contacto_campos_minimos(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Minimo",
            "phone": "1234567",
        })
        assert resp.status_code == 201
        assert resp.json()["email"] is None

    @pytest.mark.integration
    def test_crear_contacto_nombre_muy_corto(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "A",
            "phone": "1234567",
        })
        assert resp.status_code == 422


class TestObtenerContacto:

    @pytest.mark.integration
    def test_obtener_contacto_existente(self, client, auth_headers):
        headers = auth_headers()
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test Contact",
            "phone": "1234567",
        })
        contact_id = create_resp.json()["id"]

        resp = client.get(f"/api/contacts/{contact_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Contact"

    @pytest.mark.integration
    def test_obtener_contacto_inexistente(self, client):
        resp = client.get("/api/contacts/99999")
        assert resp.status_code == 404


class TestListarContactos:

    @pytest.mark.integration
    def test_listar_todos(self, client, auth_headers):
        headers = auth_headers()
        for i in range(3):
            client.post("/api/contacts", headers=headers, json={
                "name": f"Contacto {i}",
                "phone": f"12345{i}",
            })
        resp = client.get("/api/contacts")
        assert resp.status_code == 200
        assert len(resp.json()) >= 3

    @pytest.mark.integration
    def test_listar_con_limit(self, client, auth_headers):
        headers = auth_headers()
        for i in range(5):
            client.post("/api/contacts", headers=headers, json={
                "name": f"Contacto {i}",
                "phone": f"12345{i}",
            })
        resp = client.get("/api/contacts?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.integration
    def test_listar_con_limit_maximo(self, client):
        resp = client.get("/api/contacts?limit=9999")
        assert resp.status_code == 422

    @pytest.mark.integration
    def test_listar_filtrar_por_categoria(self, client, auth_headers):
        headers = auth_headers()
        client.post("/api/contacts", headers=headers, json={
            "name": "Plomero Test",
            "phone": "1234567",
            "category_id": 1,
        })
        client.post("/api/contacts", headers=headers, json={
            "name": "Gasista Test",
            "phone": "7654321",
            "category_id": 2,
        })
        resp = client.get("/api/contacts?category_id=1")
        assert resp.status_code == 200
        for c in resp.json():
            assert c["category_id"] == 1


class TestActualizarContacto:

    @pytest.mark.integration
    def test_actualizar_propio_contacto(self, client, auth_headers):
        headers = auth_headers()
        create = client.post("/api/contacts", headers=headers, json={
            "name": "Original",
            "phone": "1234567",
        })
        cid = create.json()["id"]

        resp = client.put(f"/api/contacts/{cid}", headers=headers, json={
            "name": "Modificado",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Modificado"

    @pytest.mark.integration
    def test_actualizar_contacto_ajeno_sin_permiso(self, client, auth_headers):
        headers1 = auth_headers(username="user1", email="u1@test.com")
        headers2 = auth_headers(username="user2", email="u2@test.com")

        create = client.post("/api/contacts", headers=headers1, json={
            "name": "De user1",
            "phone": "1234567",
        })
        cid = create.json()["id"]

        resp = client.put(f"/api/contacts/{cid}", headers=headers2, json={
            "name": "Modificado por user2",
        })
        assert resp.status_code == 403


class TestEliminarContacto:

    @pytest.mark.integration
    def test_eliminar_propio_contacto(self, client, auth_headers):
        headers = auth_headers()
        create = client.post("/api/contacts", headers=headers, json={
            "name": "A eliminar",
            "phone": "1234567",
        })
        cid = create.json()["id"]

        resp = client.delete(f"/api/contacts/{cid}", headers=headers)
        assert resp.status_code == 204

        resp = client.get(f"/api/contacts/{cid}")
        assert resp.status_code == 404

    @pytest.mark.integration
    def test_eliminar_contacto_ajeno(self, client, auth_headers):
        headers1 = auth_headers(username="owner", email="owner@test.com")
        headers2 = auth_headers(username="other", email="other@test.com")

        create = client.post("/api/contacts", headers=headers1, json={
            "name": "No eliminar",
            "phone": "1234567",
        })
        cid = create.json()["id"]

        resp = client.delete(f"/api/contacts/{cid}", headers=headers2)
        assert resp.status_code == 403

    @pytest.mark.integration
    def test_eliminar_inexistente(self, client, auth_headers):
        headers = auth_headers()
        resp = client.delete("/api/contacts/99999", headers=headers)
        assert resp.status_code == 404
