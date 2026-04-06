"""Robustness tests — DoS resistance (large payloads, rapid requests)."""
import pytest
from tests.conftest import _bearer


class TestLargePayloads:
    def test_very_long_name(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers,
                         json={"name": "x" * 10000})
        assert r.status_code == 422

    def test_very_long_about(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers,
                         json={"name": "Test", "about": "x" * 50000})
        assert r.status_code == 422

    def test_many_fields_in_json(self, client, user_headers):
        payload = {"name": "Test"}
        for i in range(1000):
            payload[f"field_{i}"] = f"value_{i}"
        r = client.post("/api/contacts", headers=user_headers, json=payload)
        # Should not crash — extra fields are ignored
        assert r.status_code in (201, 422)

    def test_deeply_nested_json(self, client, user_headers):
        nested = {"name": "Test"}
        current = nested
        for _ in range(100):
            current["nested"] = {"key": "value"}
            current = current["nested"]
        r = client.post("/api/contacts", headers=user_headers, json=nested)
        assert r.status_code in (201, 422)


class TestRapidRequests:
    def test_rapid_search(self, client, create_contact):
        create_contact(name="Rapid Test")
        for _ in range(20):
            r = client.get("/api/contacts/search", params={"q": "Rapid"})
            assert r.status_code == 200

    def test_rapid_contact_reads(self, client, create_contact):
        c = create_contact()
        for _ in range(20):
            r = client.get(f"/api/contacts/{c.id}")
            assert r.status_code == 200

    def test_many_categories_requests(self, client):
        for _ in range(20):
            r = client.get("/api/categories")
            assert r.status_code == 200


class TestMalformedRequests:
    def test_wrong_content_type(self, client, user_headers):
        r = client.post("/api/contacts", headers={**user_headers},
                          content="name=test&phone=123")
        assert r.status_code in (400, 422)

    def test_binary_body(self, client, user_headers):
        r = client.post("/api/contacts", headers={**user_headers},
                          content=b"\x00\x01\x02\x03")
        assert r.status_code in (400, 422)
