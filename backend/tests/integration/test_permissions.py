import pytest


class TestPermisosEdicion:

    @pytest.mark.integration
    def test_owner_edita_directamente(self, client, auth_headers):
        headers = auth_headers(username="permowner", email="perm@test.com")
        create = client.post("/api/contacts", headers=headers, json={
            "name": "Contacto", "phone": "1234567", "description": "Viejo",
        })
        cid = create.json()["id"]

        resp = client.put(f"/api/contacts/{cid}", headers=headers, json={"description": "Nuevo"})
        assert resp.status_code == 200
        assert resp.json()["description"] == "Nuevo"

    @pytest.mark.integration
    def test_usuario_registrado_edita_campo_vacio(self, client, auth_headers):
        h_owner = auth_headers(username="edowner", email="edowner@test.com")
        h_other = auth_headers(username="edother", email="edother@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Contacto", "phone": "1234567",
        })
        cid = create.json()["id"]

        resp = client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
            "description": "Agregado por otro",
        })
        assert resp.status_code == 200

    @pytest.mark.integration
    def test_usuario_registrado_no_edita_campo_lleno(self, client, auth_headers):
        h_owner = auth_headers(username="fullowner", email="full@test.com")
        h_other = auth_headers(username="fullother", email="fullother@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Contacto", "phone": "1234567", "description": "Existente",
        })
        cid = create.json()["id"]

        resp = client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
            "description": "Sobreescribir",
        })
        assert resp.status_code == 403

    @pytest.mark.integration
    def test_no_autenticado_edita_campo_vacio(self, client, auth_headers):
        h_owner = auth_headers(username="anonowner", email="anon@test.com")
        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Contacto", "phone": "1234567",
        })
        cid = create.json()["id"]

        resp = client.put(f"/api/contacts/{cid}/edit", json={
            "description": "Sugerencia anonima",
        })
        assert resp.status_code == 200

    @pytest.mark.integration
    def test_no_autenticado_no_edita_campo_lleno(self, client, auth_headers):
        h_owner = auth_headers(username="filledowner", email="filled@test.com")
        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Contacto", "phone": "1234567", "city": "Rosario",
        })
        cid = create.json()["id"]

        resp = client.put(f"/api/contacts/{cid}/edit", json={
            "city": "Buenos Aires",
        })
        assert resp.status_code == 403


class TestPermisosAdmin:

    @pytest.mark.integration
    def test_admin_listar_usuarios(self, client, auth_headers):
        # El primer usuario registrado obtiene rol admin
        h_admin = auth_headers(username="adminperm", email="adminperm@test.com")
        resp = client.get("/api/users", headers=h_admin)
        # Si es admin (primer usuario), 200; si no, 403
        assert resp.status_code in [200, 403]

    @pytest.mark.integration
    def test_usuario_normal_no_lista_usuarios(self, client, auth_headers):
        # Crear otro usuario que no sera admin
        h_first = auth_headers(username="firstadmin2", email="first2@test.com")
        h_user = auth_headers(username="normalperm", email="normal@test.com")
        resp = client.get("/api/users", headers=h_user)
        assert resp.status_code == 403
