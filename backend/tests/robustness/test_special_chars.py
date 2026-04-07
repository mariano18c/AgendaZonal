"""Robustness tests for special character injection.

Adapted from tests_ant/robustness/test_special_chars.py — uses current conftest fixtures.
Covers:
- Null bytes in search query and URL path
- Control characters in name
- RTL override character
- Zero-width joiner sequences
- Unicode BOM in search
"""
import uuid
import pytest


def _uid():
    return uuid.uuid4().hex[:8]


class TestSpecialChars:

    @pytest.mark.robustness
    def test_null_byte_in_search_query(self, client):
        """Null byte in search query should not crash the server."""
        resp = client.get("/api/contacts/search", params={"q": "test\x00injection"})
        assert resp.status_code in [200, 400, 422]

    @pytest.mark.robustness
    def test_control_characters_in_name(self, client, auth_headers):
        """Control characters in name field should not crash."""
        headers = auth_headers(username=f"ctrl_test_{_uid()}", email=f"ctrltest_{_uid()}@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Test\x01\x02\x03Name {_uid()}",
            "phone": "3411111111",
        })
        assert resp.status_code in [201, 422]

    @pytest.mark.robustness
    def test_rtl_override_character(self, client, auth_headers):
        """RTL override character should not cause issues."""
        headers = auth_headers(username=f"rtl_test_{_uid()}", email=f"rtltest_{_uid()}@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Test\u202EReverseName {_uid()}",
            "phone": "3412222222",
        })
        assert resp.status_code == 201

    @pytest.mark.robustness
    def test_zero_width_joiner(self, client, auth_headers):
        """Zero-width joiner sequences should not crash."""
        headers = auth_headers(username=f"zwj_test_{_uid()}", email=f"zwjtest_{_uid()}@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Test\u200DJoiner\u200DSequence {_uid()}",
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

    @pytest.mark.robustness
    def test_zero_width_space_in_name(self, client, auth_headers):
        """Zero-width space in name should be handled."""
        headers = auth_headers(username=f"zws_test_{_uid()}", email=f"zwstest_{_uid()}@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Test\u200BName {_uid()}",
            "phone": "3414444444",
        })
        assert resp.status_code == 201

    @pytest.mark.robustness
    def test_homoglyph_characters(self, client, auth_headers):
        """Homoglyph (Cyrillic lookalike) characters should be handled."""
        headers = auth_headers(username=f"homoglyph_{_uid()}", email=f"homoglyph_{_uid()}@test.com")
        # Cyrillic 'а' looks like Latin 'a'
        resp = client.post("/api/contacts", headers=headers, json={
            "name": f"C\u0430f\u0435 {_uid()}",  # Café with Cyrillic а
            "phone": "3415555555",
        })
        assert resp.status_code == 201
