import pytest


class TestCambiosPendientes:

    @pytest.fixture
    def contact_with_pending(self, client, auth_headers):
        h_owner = auth_headers(username="pendowner", email="pend@test.com")
        h_other = auth_headers(username="pendother", email="pendother@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Contacto Test",
            "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
            "description": "Sugerencia de otro usuario",
        })

        return {"contact_id": cid, "h_owner": h_owner, "h_other": h_other}

    @pytest.mark.integration
    def test_verificar_cambio_pendiente(self, client, contact_with_pending):
        cid = contact_with_pending["contact_id"]
        h_owner = contact_with_pending["h_owner"]

        changes = client.get(f"/api/contacts/{cid}/changes", headers=h_owner).json()
        assert len(changes) >= 1
        change_id = changes[0]["id"]

        resp = client.post(f"/api/contacts/{cid}/changes/{change_id}/verify", headers=h_owner)
        assert resp.status_code == 200
        assert resp.json()["is_verified"] is True

        contact = client.get(f"/api/contacts/{cid}").json()
        assert contact["description"] == "Sugerencia de otro usuario"

    @pytest.mark.integration
    def test_rechazar_cambio_pendiente(self, client, contact_with_pending):
        cid = contact_with_pending["contact_id"]
        h_owner = contact_with_pending["h_owner"]

        changes = client.get(f"/api/contacts/{cid}/changes", headers=h_owner).json()
        change_id = changes[0]["id"]

        resp = client.post(f"/api/contacts/{cid}/changes/{change_id}/reject", headers=h_owner)
        assert resp.status_code == 200

        contact = client.get(f"/api/contacts/{cid}").json()
        assert contact["description"] is None

    @pytest.mark.integration
    def test_eliminar_cambio_por_creador(self, client, contact_with_pending):
        cid = contact_with_pending["contact_id"]
        h_owner = contact_with_pending["h_owner"]
        h_other = contact_with_pending["h_other"]

        # Owner puede ver los cambios pendientes
        changes = client.get(f"/api/contacts/{cid}/changes", headers=h_owner).json()
        change_id = changes[0]["id"]

        # El creador (h_other) puede eliminar su propio cambio
        resp = client.delete(f"/api/contacts/{cid}/changes/{change_id}", headers=h_other)
        assert resp.status_code == 200

    @pytest.mark.integration
    def test_no_eliminar_cambio_de_otro(self, client, contact_with_pending):
        cid = contact_with_pending["contact_id"]
        h_owner = contact_with_pending["h_owner"]

        changes = client.get(f"/api/contacts/{cid}/changes", headers=h_owner).json()
        change_id = changes[0]["id"]

        resp = client.delete(f"/api/contacts/{cid}/changes/{change_id}", headers=h_owner)
        assert resp.status_code == 403


class TestHistorial:

    @pytest.mark.integration
    def test_historial_registra_cambios(self, client, auth_headers):
        headers = auth_headers(username="histuser", email="hist@test.com")
        create = client.post("/api/contacts", headers=headers, json={
            "name": "Original",
            "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}", headers=headers, json={"name": "Modificado"})

        resp = client.get(f"/api/contacts/{cid}/history", headers=headers)
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) >= 1

    @pytest.mark.integration
    def test_historial_requiere_autenticacion(self, client, auth_headers):
        headers = auth_headers(username="histauth", email="histauth@test.com")
        create = client.post("/api/contacts", headers=headers, json={
            "name": "Test", "phone": "1234567",
        })
        cid = create.json()["id"]

        # Clear cookies to ensure no auth is sent
        client.cookies.clear()
        resp = client.get(f"/api/contacts/{cid}/history")
        assert resp.status_code == 401
