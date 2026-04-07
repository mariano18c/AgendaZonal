"""Robustness tests — Unicode, boundary values, empty payloads."""
import pytest
from tests.conftest import _bearer


class TestUnicodeHandling:
    """Verify the system handles international characters correctly."""

    @pytest.mark.parametrize("name", [
        "Peluquería María",
        "Café & Más",
        "Ñoño's Place",
        "东京ラーメン",
        "مطعم عربي",
        "Ferretería «El Tornillo»",
        "🔧 Plomería Pro 🔧",
    ])
    def test_unicode_contact_names(self, client, user_headers, name):
        r = client.post("/api/contacts", headers=user_headers,
                         json={"name": name})
        assert r.status_code == 201
        assert r.json()["name"]  # Non-empty after sanitization

    def test_unicode_in_search(self, client, create_contact):
        create_contact(name="Café Ñoño")
        r = client.get("/api/contacts/search", params={"q": "Ñoño"})
        assert r.status_code == 200

    def test_unicode_in_description(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers,
                         json={"name": "Test", "description": "Descripción con ñ y ü"})
        assert r.status_code == 201


class TestBoundaryValues:
    def test_skip_zero(self, client):
        r = client.get("/api/contacts", params={"skip": 0, "limit": 1})
        assert r.status_code == 200

    def test_limit_max(self, client):
        r = client.get("/api/contacts", params={"limit": 100})
        assert r.status_code == 200

    def test_limit_negative(self, client):
        r = client.get("/api/contacts", params={"limit": -1})
        assert r.status_code in (200, 422)

    def test_skip_very_large(self, client):
        r = client.get("/api/contacts", params={"skip": 999999})
        assert r.status_code == 200
        assert r.json()["contacts"] == []

    def test_contact_id_zero(self, client):
        r = client.get("/api/contacts/0")
        assert r.status_code == 404

    def test_contact_id_negative(self, client):
        r = client.get("/api/contacts/-1")
        assert r.status_code in (404, 422)

    def test_contact_id_very_large(self, client):
        r = client.get("/api/contacts/2147483647")
        assert r.status_code == 404

    def test_latitude_at_boundary(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers,
                         json={"name": "Edge", "latitude": 90.0, "longitude": 180.0})
        assert r.status_code == 201

    def test_geo_radius_zero(self, client):
        r = client.get("/api/contacts/search",
                        params={"lat": 0, "lon": 0, "radius_km": 0})
        assert r.status_code in (200, 400, 422)


class TestEmptyPayloads:
    def test_empty_json(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers, json={})
        assert r.status_code == 422

    def test_empty_update(self, client, create_user, create_contact):
        user = create_user()
        c = create_contact(user_id=user.id)
        r = client.put(f"/api/contacts/{c.id}", headers=_bearer(user), json={})
        # Empty update should be accepted (no changes)
        assert r.status_code in (200, 422)

    def test_empty_review(self, client, create_user, create_contact):
        u = create_user()
        c = create_contact()
        r = client.post(f"/api/contacts/{c.id}/reviews",
                         headers=_bearer(u), json={})
        assert r.status_code == 422


class TestSpecialCharacters:
    @pytest.mark.parametrize("char", [
        "\x00",     # Null byte
        "\r\n",     # CRLF
        "\t",       # Tab
        "\x1b[31m", # ANSI escape
    ])
    def test_control_chars_in_name(self, client, user_headers, char):
        r = client.post("/api/contacts", headers=user_headers,
                         json={"name": f"Test{char}Name"})
        assert r.status_code in (201, 422, 400)
        if r.status_code == 201:
            assert r.json()["name"] is not None


class TestSpecialCharsAdvanced:
    """Advanced special character injection — merged from tests_ant."""

    def test_null_byte_in_search_query(self, client):
        """Null byte in search query should not crash the server."""
        resp = client.get("/api/contacts/search", params={"q": "test\x00injection"})
        assert resp.status_code in [200, 400, 422]

    def test_rtl_override_character(self, client, auth_headers):
        """RTL override character should not cause issues."""
        headers = auth_headers(username="rtl_test", email="rtltest@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test\u202EReverseName",
            "phone": "3412222222",
        })
        assert resp.status_code == 201

    def test_zero_width_joiner(self, client, auth_headers):
        """Zero-width joiner sequences should not crash."""
        headers = auth_headers(username="zwj_test", email="zwjtest@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test\u200DJoiner\u200DSequence",
            "phone": "3413333333",
        })
        assert resp.status_code == 201

    def test_null_byte_in_url_path(self, client):
        """Null byte in URL path should not crash."""
        resp = client.get("/api/contacts/search", params={"q": "\x00"})
        assert resp.status_code in [200, 400, 422]

    def test_unicode_bom_in_search(self, client):
        """Unicode BOM in search query should not crash."""
        resp = client.get("/api/contacts/search", params={"q": "\ufefftest"})
        assert resp.status_code in [200, 400, 422]
