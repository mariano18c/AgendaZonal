"""Robustness tests for special character injection."""
import pytest


class TestSpecialChars:
    """Null bytes, control characters, and special sequences."""

    @pytest.mark.robustness
    def test_null_byte_in_search_query(self, client):
        """Null byte in search query should not crash the server."""
        resp = client.get("/api/contacts/search", params={"q": "test\x00injection"})
        assert resp.status_code in [200, 400, 422]

    @pytest.mark.robustness
    def test_control_characters_in_name(self, client, auth_headers):
        """Control characters in name field should not crash."""
        headers = auth_headers(username="ctrl_test", email="ctrltest@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test\x01\x02\x03Name",
            "phone": "3411111111",
        })
        assert resp.status_code in [201, 422]

    @pytest.mark.robustness
    def test_rtl_override_character(self, client, auth_headers):
        """RTL override character should not cause issues."""
        headers = auth_headers(username="rtl_test", email="rtltest@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test\u202EReverseName",
            "phone": "3412222222",
        })
        assert resp.status_code == 201

    @pytest.mark.robustness
    def test_zero_width_joiner(self, client, auth_headers):
        """Zero-width joiner sequences should not crash."""
        headers = auth_headers(username="zwj_test", email="zwjtest@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test\u200DJoiner\u200DSequence",
            "phone": "3413333333",
        })
        assert resp.status_code == 201

    @pytest.mark.robustness
    def test_null_byte_in_url_path(self, client):
        """Null byte in URL path should not crash."""
        resp = client.get("/api/contacts/search", params={"q": "\x00"})
        assert resp.status_code in [200, 400, 422]

    @pytest.mark.robustness
    def test_unicode_bom_in_search(self, client):
        """Unicode BOM in search query should not crash."""
        resp = client.get("/api/contacts/search", params={"q": "\ufefftest"})
        assert resp.status_code in [200, 400, 422]
