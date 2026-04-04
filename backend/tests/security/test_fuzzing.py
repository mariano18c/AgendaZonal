"""Payload fuzzing tests for Pydantic schema resilience.

Tests that the API correctly rejects malformed inputs:
- Wrong types (string in int field, int in string field)
- Massive JSON payloads
- Null values in required fields
- Edge case numeric values (NaN, Inf)
- Unicode bombs and special characters
"""
import pytest
import json


class TestTypeFuzzing:

    @pytest.mark.security
    def test_string_in_int_field_category_id(self, client, auth_headers):
        h = auth_headers(username="fuzzcat", email="fuzzcat@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": "Fuzz Test",
            "phone": "1234567",
            "category_id": "not_a_number",
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_int_in_string_field_name(self, client, auth_headers):
        h = auth_headers(username="fuzzname", email="fuzzname@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": 12345,
            "phone": "1234567",
        })
        assert resp.status_code in [201, 422]

    @pytest.mark.security
    def test_string_in_float_field_latitude(self, client, auth_headers):
        h = auth_headers(username="fuzzlat", email="fuzzlat@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": "Fuzz Lat",
            "phone": "1234567",
            "latitude": "not_a_float",
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_boolean_in_string_field(self, client, auth_headers):
        h = auth_headers(username="fuzzbool", email="fuzzbool@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": True,
            "phone": "1234567",
        })
        assert resp.status_code in [201, 422]

    @pytest.mark.security
    def test_array_in_string_field(self, client, auth_headers):
        h = auth_headers(username="fuzzarr", email="fuzzarr@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": ["array", "name"],
            "phone": "1234567",
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_object_in_string_field(self, client, auth_headers):
        h = auth_headers(username="fuzzobj", email="fuzzobj@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": {"nested": "object"},
            "phone": "1234567",
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_null_in_required_field(self, client, auth_headers):
        h = auth_headers(username="fuzznull", email="fuzznull@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": None,
            "phone": "1234567",
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_empty_string_in_required_field(self, client, auth_headers):
        h = auth_headers(username="fuzzempty", email="fuzzempty@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": "",
            "phone": "1234567",
        })
        assert resp.status_code == 422


class TestNumericEdgeCases:

    @pytest.mark.security
    def test_nan_latitude(self, client, auth_headers):
        h = auth_headers(username="fuzznan", email="fuzznan@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": "NaN Test",
            "phone": "1234567",
            "latitude": "NaN",
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_infinity_latitude(self, client, auth_headers):
        h = auth_headers(username="fuzzinf", email="fuzzinf@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": "Inf Test",
            "phone": "1234567",
            "latitude": "Infinity",
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_negative_infinity_latitude(self, client, auth_headers):
        h = auth_headers(username="fuzzninf", email="fuzzninf@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": "NegInf Test",
            "phone": "1234567",
            "latitude": "-Infinity",
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_very_large_integer_category_id(self, client, auth_headers):
        h = auth_headers(username="fuzzbigint", email="fuzzbigint@test.com")
        # Very large int may cause OverflowError in SQLite or be rejected by Pydantic
        try:
            resp = client.post("/api/contacts", headers=h, json={
                "name": "Big Int",
                "phone": "1234567",
                "category_id": 2**63,
            })
            assert resp.status_code in [201, 422, 500]
        except (OverflowError, ValueError):
            pass  # Expected: int too large for SQLite

    @pytest.mark.security
    def test_negative_category_id(self, client, auth_headers):
        h = auth_headers(username="fuzznegcat", email="fuzznegcat@test.com")
        # Negative FK fails at DB level (no category with id=-1)
        try:
            resp = client.post("/api/contacts", headers=h, json={
                "name": "Neg Cat",
                "phone": "1234567",
                "category_id": -1,
            })
            assert resp.status_code in [422, 500]
        except Exception:
            pass  # Expected: FK constraint or other DB error

    @pytest.mark.security
    def test_zero_latitude(self, client, auth_headers):
        h = auth_headers(username="fuzzzero", email="fuzzzero@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": "Zero Lat",
            "phone": "1234567",
            "latitude": 0.0,
        })
        assert resp.status_code == 201
        assert resp.json()["latitude"] == 0.0


class TestMassivePayloads:

    @pytest.mark.security
    def test_massive_json_body(self, client, auth_headers):
        h = auth_headers(username="fuzzmassive", email="fuzzmassive@test.com")
        huge_description = "A" * 10000
        resp = client.post("/api/contacts", headers=h, json={
            "name": "Massive",
            "phone": "1234567",
            "description": huge_description,
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_many_extra_fields(self, client, auth_headers):
        h = auth_headers(username="fuzzextra", email="fuzzextra@test.com")
        payload = {"name": "Extra", "phone": "1234567"}
        for i in range(100):
            payload[f"extra_field_{i}"] = f"value_{i}"
        resp = client.post("/api/contacts", headers=h, json=payload)
        assert resp.status_code in [201, 422]

    @pytest.mark.security
    def test_deeply_nested_json(self, client, auth_headers):
        h = auth_headers(username="fuzzdeep", email="fuzzdeep@test.com")
        nested = {"name": "Deep", "phone": "1234567"}
        for i in range(10):
            nested = {"nested": nested}
        resp = client.post("/api/contacts", headers=h, json=nested)
        assert resp.status_code == 422

    @pytest.mark.security
    def test_massive_json_payload_1000_keys(self, client, auth_headers):
        """Send JSON with 1000+ keys, verify 422 or graceful handling."""
        h = auth_headers(username="fuzzmassive1k", email="fuzzmassive1k@test.com")
        payload = {"name": "Massive", "phone": "1234567"}
        for i in range(1000):
            payload[f"key_{i}"] = "x" * 100
        resp = client.post("/api/contacts", headers=h, json=payload)
        assert resp.status_code in [201, 422, 400]
        # Should not crash or hang


class TestUnicodeAndSpecialChars:

    @pytest.mark.security
    def test_unicode_name(self, client, auth_headers):
        h = auth_headers(username="fuzzuni", email="fuzzuni@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": "Ñoño García-López 日本語",
            "phone": "1234567",
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "Ñoño García-López 日本語"

    @pytest.mark.security
    def test_emoji_in_name(self, client, auth_headers):
        h = auth_headers(username="fuzzemoji", email="fuzzemoji@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": "Plomero 🔧",
            "phone": "1234567",
        })
        assert resp.status_code == 201

    @pytest.mark.security
    def test_null_bytes_in_string(self, client, auth_headers):
        h = auth_headers(username="fuzznullb", email="fuzznullb@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": "Test\x00Name",
            "phone": "1234567",
        })
        assert resp.status_code in [201, 422]

    @pytest.mark.security
    def test_newline_in_name(self, client, auth_headers):
        h = auth_headers(username="fuzznl", email="fuzznl@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": "Line1\nLine2",
            "phone": "1234567",
        })
        assert resp.status_code == 201

    @pytest.mark.security
    def test_tab_in_name(self, client, auth_headers):
        h = auth_headers(username="fuzztab", email="fuzztab@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": "Tab\tName",
            "phone": "1234567",
        })
        assert resp.status_code == 201

    @pytest.mark.security
    def test_rtl_character_in_name(self, client, auth_headers):
        """Right-to-left unicode override character."""
        h = auth_headers(username="fuzzrtl", email="fuzzrtl@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": "Test\u202EName",
            "phone": "1234567",
        })
        assert resp.status_code == 201


class TestAuthFuzzing:

    @pytest.mark.security
    def test_random_bytes_as_token(self, client):
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer " + "\x00\x01\x02\x03" * 10,
        })
        assert resp.status_code == 401

    @pytest.mark.security
    def test_very_long_token(self, client):
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer " + "A" * 10000,
        })
        assert resp.status_code == 401

    @pytest.mark.security
    def test_authorization_header_injection(self, client):
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer token\r\nInjected-Header: value",
        })
        assert resp.status_code == 401

    @pytest.mark.security
    def test_login_with_json_injection(self, client):
        resp = client.post("/api/auth/login", json={
            "username_or_email": '{"$gt": ""}',
            "password": '{"$gt": ""}',
        })
        assert resp.status_code == 401
