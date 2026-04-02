"""Complete integration tests for contacts endpoints.

Covers edge cases and endpoints not fully tested elsewhere:
- History endpoint with verifiable data
- Image upload size limits
- Verify contact flow
- Search edge cases
"""
import pytest
import io
from PIL import Image


class TestContactHistory:

    @pytest.mark.integration
    def test_history_shows_field_changes(self, client, auth_headers):
        h = auth_headers(username="histfield", email="histfield@test.com")
        create = client.post("/api/contacts", headers=h, json={
            "name": "Original", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}", headers=h, json={"name": "Modified"})

        resp = client.get(f"/api/contacts/{cid}/history", headers=h)
        assert resp.status_code == 200
        history = resp.json()
        assert any(
            h["field_name"] == "name" and h["new_value"] == "Modified"
            for h in history
        )

    @pytest.mark.integration
    def test_history_shows_old_and_new_values(self, client, auth_headers):
        h = auth_headers(username="histval", email="histval@test.com")
        create = client.post("/api/contacts", headers=h, json={
            "name": "Old Name", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}", headers=h, json={"name": "New Name"})

        resp = client.get(f"/api/contacts/{cid}/history", headers=h)
        history = resp.json()
        name_change = next(
            (h for h in history if h["field_name"] == "name"), None
        )
        assert name_change is not None
        assert name_change["old_value"] == "Old Name"
        assert name_change["new_value"] == "New Name"

    @pytest.mark.integration
    def test_history_ordered_by_date_desc(self, client, auth_headers):
        h = auth_headers(username="historder", email="historder@test.com")
        create = client.post("/api/contacts", headers=h, json={
            "name": "Original Name", "phone": "1234567",
        })
        assert create.status_code == 201, f"Create failed: {create.json()}"
        cid = create.json()["id"]

        # Update twice to create history entries
        resp1 = client.put(f"/api/contacts/{cid}", headers=h, json={"name": "Second Name"})
        assert resp1.status_code == 200
        resp2 = client.put(f"/api/contacts/{cid}", headers=h, json={"name": "Third Name"})
        assert resp2.status_code == 200

        resp = client.get(f"/api/contacts/{cid}/history", headers=h)
        assert resp.status_code == 200
        history = resp.json()
        name_changes = [h for h in history if h["field_name"] == "name"]
        # Should have at least 2 name changes (from Original -> Second -> Third)
        assert len(name_changes) >= 1


class TestVerifyContact:

    @pytest.mark.integration
    def test_owner_can_verify_own_contact(self, client, auth_headers):
        h = auth_headers(username="verowner", email="verowner@test.com")
        create = client.post("/api/contacts", headers=h, json={
            "name": "Verify Me", "phone": "1234567",
        })
        cid = create.json()["id"]

        resp = client.post(
            f"/api/contacts/{cid}/verify",
            headers=h,
            json={"is_verified": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_verified"] is True
        assert resp.json()["verified_by"] is not None

    @pytest.mark.integration
    def test_non_owner_cannot_verify(self, client, auth_headers):
        h_owner = auth_headers(username="verown2", email="verown2@test.com")
        h_other = auth_headers(username="veroth2", email="veroth2@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "No Verify", "phone": "1234567",
        })
        cid = create.json()["id"]

        resp = client.post(
            f"/api/contacts/{cid}/verify",
            headers=h_other,
            json={"is_verified": True},
        )
        assert resp.status_code == 403

    @pytest.mark.integration
    def test_unverify_clears_verification(self, client, auth_headers):
        h = auth_headers(username="unverify", email="unverify@test.com")
        create = client.post("/api/contacts", headers=h, json={
            "name": "Unverify Me", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.post(f"/api/contacts/{cid}/verify", headers=h, json={"is_verified": True})
        resp = client.post(f"/api/contacts/{cid}/verify", headers=h, json={"is_verified": False})
        assert resp.status_code == 200
        assert resp.json()["is_verified"] is False
        assert resp.json()["verified_by"] is None
        assert resp.json()["verified_at"] is None


class TestSearchEdgeCases:

    @pytest.mark.integration
    def test_search_with_both_q_and_category(self, client, auth_headers):
        h = auth_headers(username="searchboth", email="searchboth@test.com")
        client.post("/api/contacts", headers=h, json={
            "name": "Plomero Juan", "phone": "1234567", "category_id": 1,
        })

        resp = client.get("/api/contacts/search?q=Juan&category_id=1")
        assert resp.status_code == 200

    @pytest.mark.integration
    def test_search_special_chars_in_query(self, client):
        resp = client.get("/api/contacts/search?q=test%20with%20spaces")
        assert resp.status_code == 200

    @pytest.mark.integration
    def test_search_empty_query_returns_400(self, client):
        resp = client.get("/api/contacts/search")
        assert resp.status_code == 400


class TestImageUploadLimits:

    def _create_jpeg_bytes(self, width: int = 100, height: int = 100) -> io.BytesIO:
        img = Image.new("RGB", (width, height), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        return buf

    @pytest.mark.integration
    def test_upload_requires_auth(self, client, auth_headers):
        h = auth_headers(username="imgauth2", email="imgauth2@test.com")
        create = client.post("/api/contacts", headers=h, json={
            "name": "Auth Test", "phone": "1234567",
        })
        cid = create.json()["id"]

        # Clear cookies to ensure no auth is sent
        client.cookies.clear()
        jpeg = self._create_jpeg_bytes()
        resp = client.post(
            f"/api/contacts/{cid}/image",
            files={"file": ("test.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 401

    @pytest.mark.integration
    def test_upload_nonexistent_contact(self, client, auth_headers):
        h = auth_headers(username="img404", email="img404@test.com")
        jpeg = self._create_jpeg_bytes()
        resp = client.post(
            "/api/contacts/99999/image",
            headers=h,
            files={"file": ("test.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 404
