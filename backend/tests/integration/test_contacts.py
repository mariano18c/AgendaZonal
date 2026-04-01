"""Integration tests for contacts CRUD and the pending-changes workflow.

Covers:
- Create, read, update, delete contacts
- Edit with permission checks (edit endpoint)
- Reject and delete pending changes
- History tracking
"""
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

    @pytest.mark.integration
    def test_crear_contacto_con_todos_los_campos(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Completo",
            "phone": "1234567",
            "email": "test@test.com",
            "address": "Calle 123",
            "city": "Rosario",
            "neighborhood": "Centro",
            "category_id": 1,
            "description": "Descripcion de prueba",
            "schedule": "Lun-Vie 8-18",
            "website": "https://example.com",
            "latitude": -34.6,
            "longitude": -58.38,
            "maps_url": "https://maps.google.com",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["city"] == "Rosario"
        assert data["latitude"] == -34.6


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

    @pytest.mark.integration
    def test_listar_con_skip(self, client, auth_headers):
        headers = auth_headers()
        for i in range(5):
            client.post("/api/contacts", headers=headers, json={
                "name": f"Skip{i}",
                "phone": f"12345{i}",
            })
        all_resp = client.get("/api/contacts")
        skip_resp = client.get("/api/contacts?skip=2&limit=100")
        assert len(skip_resp.json()) == len(all_resp.json()) - 2


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

    @pytest.mark.integration
    def test_actualizar_multiples_campos(self, client, auth_headers):
        headers = auth_headers()
        create = client.post("/api/contacts", headers=headers, json={
            "name": "Original",
            "phone": "1234567",
            "city": "Buenos Aires",
        })
        cid = create.json()["id"]

        resp = client.put(f"/api/contacts/{cid}", headers=headers, json={
            "name": "Nuevo",
            "phone": "7654321",
            "city": "Rosario",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Nuevo"
        assert data["phone"] == "7654321"
        assert data["city"] == "Rosario"

    @pytest.mark.integration
    def test_actualizar_contacto_inexistente(self, client, auth_headers):
        headers = auth_headers()
        resp = client.put("/api/contacts/99999", headers=headers, json={
            "name": "No existe",
        })
        assert resp.status_code == 404


class TestEliminarContacto:

    @pytest.mark.integration
    def test_eliminar_propio_contacto(self, client, auth_headers):
        headers = auth_headers()
        create = client.post("/api/contacts", headers=headers, json={
            "name": "A eliminar",
            "phone": "1234567",
        })
        cid = create.json()["id"]

        # First, request deletion to flag the contact
        flag_resp = client.post(f"/api/contacts/{cid}/request-deletion", headers=headers)
        assert flag_resp.status_code == 200

        # Then, delete the flagged contact
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


class TestRejectChange:

    @pytest.mark.integration
    def test_owner_rejects_pending_change(self, client, auth_headers):
        h_owner = auth_headers(username="rejown", email="rejown@test.com")
        h_other = auth_headers(username="rejoth", email="rejoth@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Reject Test", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
            "description": "Sugerencia a rechazar",
        })

        changes = client.get(f"/api/contacts/{cid}/changes", headers=h_owner).json()
        change_id = changes[0]["id"]

        resp = client.post(f"/api/contacts/{cid}/changes/{change_id}/reject", headers=h_owner)
        assert resp.status_code == 200
        assert resp.json()["is_verified"] is True

    @pytest.mark.integration
    def test_non_owner_cannot_reject_change(self, client, auth_headers):
        h_owner = auth_headers(username="rejown2", email="rejown2@test.com")
        h_other = auth_headers(username="rejoth2", email="rejoth2@test.com")
        h_stranger = auth_headers(username="rejstr", email="rejstr@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Reject Auth", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
            "description": "Cambio",
        })

        changes = client.get(f"/api/contacts/{cid}/changes", headers=h_owner).json()
        change_id = changes[0]["id"]

        resp = client.post(f"/api/contacts/{cid}/changes/{change_id}/reject", headers=h_stranger)
        assert resp.status_code == 403

    @pytest.mark.integration
    def test_reject_nonexistent_change(self, client, auth_headers):
        h_owner = auth_headers(username="rej404", email="rej404@test.com")
        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "No Change", "phone": "1234567",
        })
        cid = create.json()["id"]

        resp = client.post(f"/api/contacts/{cid}/changes/99999/reject", headers=h_owner)
        assert resp.status_code == 404

    @pytest.mark.integration
    def test_reject_already_verified_change(self, client, auth_headers):
        h_owner = auth_headers(username="rejver", email="rejver@test.com")
        h_other = auth_headers(username="rejveroth", email="rejveroth@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Already Ver", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
            "description": "Will verify first",
        })

        changes = client.get(f"/api/contacts/{cid}/changes", headers=h_owner).json()
        change_id = changes[0]["id"]

        client.post(f"/api/contacts/{cid}/changes/{change_id}/verify", headers=h_owner)
        resp = client.post(f"/api/contacts/{cid}/changes/{change_id}/reject", headers=h_owner)
        assert resp.status_code == 404


class TestDeleteChange:

    @pytest.mark.integration
    def test_creator_deletes_own_pending_change(self, client, auth_headers):
        h_owner = auth_headers(username="delown", email="delown@test.com")
        h_other = auth_headers(username="deloth", email="deloth@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Delete Change", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
            "description": "Cambio temporal",
        })

        # Owner sees the changes (has permission)
        changes = client.get(f"/api/contacts/{cid}/changes", headers=h_owner).json()
        assert len(changes) >= 1
        change_id = changes[0]["id"]

        # The creator (h_other) deletes their own change
        resp = client.delete(f"/api/contacts/{cid}/changes/{change_id}", headers=h_other)
        assert resp.status_code == 200

    @pytest.mark.integration
    def test_non_creator_cannot_delete_change(self, client, auth_headers):
        h_owner = auth_headers(username="delown2", email="delown2@test.com")
        h_other = auth_headers(username="deloth2", email="deloth2@test.com")
        h_stranger = auth_headers(username="delstr", email="delstr@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "No Delete", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
            "description": "Cambio ajeno",
        })

        # Owner sees the changes
        changes = client.get(f"/api/contacts/{cid}/changes", headers=h_owner).json()
        assert len(changes) >= 1
        change_id = changes[0]["id"]

        # Stranger cannot delete another user's change
        resp = client.delete(f"/api/contacts/{cid}/changes/{change_id}", headers=h_stranger)
        assert resp.status_code == 403

    @pytest.mark.integration
    def test_delete_nonexistent_change(self, client, auth_headers):
        h_owner = auth_headers(username="del404", email="del404@test.com")
        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "No Change Del", "phone": "1234567",
        })
        cid = create.json()["id"]

        resp = client.delete(f"/api/contacts/{cid}/changes/99999", headers=h_owner)
        assert resp.status_code == 404


class TestEditContactEndpoint:

    @pytest.mark.integration
    def test_owner_edit_directly(self, client, auth_headers):
        h = auth_headers(username="editown", email="editown@test.com")
        create = client.post("/api/contacts", headers=h, json={
            "name": "Original", "phone": "1234567",
        })
        cid = create.json()["id"]

        resp = client.put(f"/api/contacts/{cid}/edit", headers=h, json={
            "name": "Direct Edit",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Direct Edit"

    @pytest.mark.integration
    def test_anonymous_edit_empty_field_creates_pending(self, client, auth_headers):
        h_owner = auth_headers(username="anonown", email="anonown@test.com")
        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Anon Edit", "phone": "1234567",
        })
        cid = create.json()["id"]

        resp = client.put(f"/api/contacts/{cid}/edit", json={
            "description": "Sugerencia anonima",
        })
        assert resp.status_code == 200

        contact = client.get(f"/api/contacts/{cid}").json()
        assert contact["pending_changes_count"] == 1
        assert contact["description"] is None

    @pytest.mark.integration
    def test_anonymous_edit_filled_field_rejected(self, client, auth_headers):
        h_owner = auth_headers(username="anonfil", email="anonfil@test.com")
        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Filled", "phone": "1234567", "description": "Existente",
        })
        cid = create.json()["id"]

        resp = client.put(f"/api/contacts/{cid}/edit", json={
            "description": "Sobreescribir",
        })
        assert resp.status_code == 403

    @pytest.mark.integration
    def test_edit_nonexistent_contact(self, client, auth_headers):
        h = auth_headers(username="edit404", email="edit404@test.com")
        resp = client.put("/api/contacts/99999/edit", headers=h, json={
            "name": "No existe",
        })
        assert resp.status_code == 404
