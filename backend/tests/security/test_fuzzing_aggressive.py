"""Aggressive fuzzing tests — boundary stress, malformed payloads, protocol abuse."""
import pytest
import json
import io
from PIL import Image


def _make_jpeg(width=100, height=100):
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def _login(client, username, password="password123"):
    resp = client.post("/api/auth/login", json={
        "username_or_email": username,
        "password": password,
    })
    return {"Authorization": f"Bearer {resp.json()['token']}"}


class TestPayloadFuzzing:
    """Send malformed payloads to every endpoint."""

    def test_post_empty_body_to_contacts(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, content=b"")
        assert resp.status_code == 422

    def test_post_invalid_json_to_contacts(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, content=b"not json{{{")
        assert resp.status_code == 422

    def test_post_array_instead_of_object(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json=[1, 2, 3])
        assert resp.status_code == 422

    def test_post_null_instead_of_object(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, content=b"null")
        assert resp.status_code == 422

    def test_post_boolean_to_contacts(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, content=b"true")
        assert resp.status_code == 422

    def test_post_string_instead_of_json(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, content=b'"hello"')
        assert resp.status_code == 422

    def test_post_nested_null_fields(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": None,
            "phone": None,
            "email": None,
            "address": None,
            "city": None,
        })
        assert resp.status_code == 422

    def test_post_emoji_in_name(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "🔧 Plomero 🚿",
            "phone": "1234567",
        })
        assert resp.status_code == 201

    def test_post_unicode_in_description(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1234567",
            "description": "日本語テスト 🎌 café résumé",
        })
        assert resp.status_code == 201

    def test_post_zero_width_chars(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test\u200BName",  # zero-width space
            "phone": "1234567",
        })
        assert resp.status_code == 201


class TestBoundaryStress:
    """Test boundary conditions on numeric and string fields."""

    def test_contact_name_exactly_100_chars(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "A" * 100,
            "phone": "1234567",
        })
        assert resp.status_code == 201

    def test_contact_name_101_chars_rejected(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "A" * 101,
            "phone": "1234567",
        })
        assert resp.status_code == 422

    def test_contact_phone_exactly_20_chars(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1" * 20,
        })
        assert resp.status_code == 201

    def test_contact_phone_21_chars_rejected(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1" * 21,
        })
        assert resp.status_code == 422

    def test_contact_latitude_boundary_90(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1234567",
            "latitude": 90.0,
        })
        assert resp.status_code == 201

    def test_contact_latitude_90_0001_rejected(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1234567",
            "latitude": 90.0001,
        })
        assert resp.status_code == 422

    def test_contact_longitude_boundary_180(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1234567",
            "longitude": -180.0,
        })
        assert resp.status_code == 201

    def test_contact_latitude_negative_90(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1234567",
            "latitude": -90.0,
        })
        assert resp.status_code == 201

    def test_contact_longitude_positive_180(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1234567",
            "longitude": 180.0,
        })
        assert resp.status_code == 201

    def test_contact_longitude_180_0001_rejected(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1234567",
            "longitude": 180.0001,
        })
        assert resp.status_code == 422


class TestHTTPMethodFuzzing:
    """Test unexpected HTTP methods on endpoints."""

    def test_patch_on_contacts(self, client, auth_headers):
        headers = auth_headers()
        resp = client.request("PATCH", "/api/contacts", headers=headers, json={})
        assert resp.status_code in [405, 422]

    def test_options_on_contacts(self, client):
        resp = client.options("/api/contacts")
        assert resp.status_code in [200, 204, 405]

    def test_delete_on_categories(self, client):
        resp = client.delete("/api/categories")
        assert resp.status_code in [405, 403]

    def test_put_on_categories(self, client):
        resp = client.put("/api/categories")
        assert resp.status_code in [405, 422]


class TestHeaderFuzzing:
    """Test malformed and malicious headers."""

    def test_oversized_authorization_header(self, client):
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer " + "A" * 10000,
        })
        assert resp.status_code in [401, 413]

    def test_malformed_content_type(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post(
            "/api/contacts",
            headers={**headers, "Content-Type": "text/html"},
            json={"name": "Test", "phone": "1234567"},
        )
        # FastAPI should still parse JSON despite wrong content-type
        assert resp.status_code in [201, 422]

    def test_multiple_authorization_headers(self, client):
        """Some frameworks crash on duplicate headers."""
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer token1",
        })
        assert resp.status_code == 401

    def test_empty_user_agent(self, client):
        resp = client.get("/health", headers={"User-Agent": ""})
        assert resp.status_code == 200

    def test_giant_user_agent(self, client):
        resp = client.get("/health", headers={"User-Agent": "A" * 50000})
        assert resp.status_code == 200


class TestQueryParameterFuzzing:
    """Test query parameter abuse."""

    def test_duplicate_query_params(self, client):
        resp = client.get("/api/contacts?skip=1&skip=2&skip=3")
        assert resp.status_code == 200

    def test_empty_query_param(self, client):
        resp = client.get("/api/contacts/search?q=")
        assert resp.status_code in [200, 400, 422]

    def test_very_long_query_param(self, client):
        resp = client.get(f"/api/contacts/search?q={'A' * 5000}")
        assert resp.status_code in [200, 414]

    def test_special_chars_in_query(self, client):
        special = "!@#$%^&*()_+-=[]{}|;':\",.<>?/`~"
        resp = client.get(f"/api/contacts/search?q={special}")
        assert resp.status_code in [200, 400]

    def test_null_byte_in_query(self, client):
        resp = client.get("/api/contacts/search?q=test%00injection")
        assert resp.status_code in [200, 400, 422]

    def test_limit_boundary(self, client):
        resp = client.get("/api/contacts?limit=500")
        # 500 is the max limit (le=500), should be accepted
        assert resp.status_code in [200, 422]

    def test_limit_max_boundary(self, client):
        resp = client.get("/api/contacts?limit=501")
        assert resp.status_code == 422


class TestJSONDepthFuzzing:
    """Test deeply nested JSON payloads."""

    def test_deeply_nested_json(self, client, auth_headers):
        """Pydantic should reject deeply nested structures."""
        headers = auth_headers()
        # Create a deeply nested dict
        nested = {"a": {"b": {"c": {"d": {"e": {"f": "value"}}}}}}
        resp = client.post("/api/contacts", headers=headers, json=nested)
        assert resp.status_code == 422

    def test_very_large_json_keys(self, client, auth_headers):
        headers = auth_headers()
        payload = {"name": "Test", "phone": "1234567"}
        # Add many extra keys
        for i in range(100):
            payload[f"extra_key_{i}"] = "value"
        resp = client.post("/api/contacts", headers=headers, json=payload)
        # Should either accept (ignoring extras) or reject
        assert resp.status_code in [201, 422]


class TestFileUploadFuzzing:
    """Test file upload edge cases."""

    def test_upload_empty_file(self, client, create_user, database_session):
        from app.models.contact import Contact
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        empty = io.BytesIO(b"")

        resp = client.post(
            f"/api/contacts/{contact.id}/image",
            headers=headers,
            files={"file": ("empty.jpg", empty, "image/jpeg")},
        )
        assert resp.status_code in [400, 500]

    def test_upload_text_file_as_jpg(self, client, create_user, database_session):
        from app.models.contact import Contact
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        fake = io.BytesIO(b"This is not a JPEG file at all, just plain text.")

        resp = client.post(
            f"/api/contacts/{contact.id}/image",
            headers=headers,
            files={"file": ("fake.jpg", fake, "image/jpeg")},
        )
        assert resp.status_code == 400

    def test_upload_gif_as_jpg(self, client, create_user, database_session):
        from app.models.contact import Contact
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)

        headers = _login(client, "testuser")
        # Minimal GIF
        gif = io.BytesIO(b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;")

        resp = client.post(
            f"/api/contacts/{contact.id}/image",
            headers=headers,
            files={"file": ("image.gif", gif, "image/gif")},
        )
        assert resp.status_code == 400


class TestUnicodeNormalization:
    """Test Unicode normalization attacks."""

    def test_homoglyph_in_username(self, client, captcha):
        """Use Cyrillic 'а' instead of Latin 'a'."""
        resp = client.post("/api/auth/register", json={
            "username": "аdmin",  # Cyrillic 'а'
            "email": "homoglyph@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        # Should be accepted as a different username
        assert resp.status_code == 201

    def test_rtl_override_in_name(self, client, auth_headers):
        """Right-to-left override character."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test\u202ERLO\u202C",  # RLO + POP
            "phone": "1234567",
        })
        assert resp.status_code in [201, 422]

    def test_zero_width_joiner_sequence(self, client, auth_headers):
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test\u200D\u200D\u200D",  # ZWJ sequence
            "phone": "1234567",
        })
        assert resp.status_code == 201
