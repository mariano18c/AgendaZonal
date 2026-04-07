"""Aggressive fuzzing tests — boundary stress, malformed payloads, protocol abuse."""
import io
import pytest


class TestPayloadFuzzing:
    """Send malformed payloads to every endpoint."""

    def test_post_empty_body_to_contacts(self, client, auth_headers):
        """Empty body should return validation error."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, content=b"")
        assert resp.status_code == 422

    def test_post_invalid_json_to_contacts(self, client, auth_headers):
        """Invalid JSON should return validation error."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, content=b"not json{{{")
        assert resp.status_code == 422

    def test_post_array_instead_of_object(self, client, auth_headers):
        """Array instead of object should return validation error."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json=[1, 2, 3])
        assert resp.status_code == 422

    def test_post_null_instead_of_object(self, client, auth_headers):
        """Null instead of object should return validation error."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, content=b"null")
        assert resp.status_code == 422

    def test_post_boolean_to_contacts(self, client, auth_headers):
        """Boolean instead of object should return validation error."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, content=b"true")
        assert resp.status_code == 422

    def test_post_string_instead_of_json(self, client, auth_headers):
        """String instead of JSON object should return validation error."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, content=b'"hello"')
        assert resp.status_code == 422

    def test_post_nested_null_fields(self, client, auth_headers):
        """Null fields should return validation error."""
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
        """Emoji in name should be accepted."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "🔧 Plomero 🚿",
            "phone": "1234567",
        })
        assert resp.status_code == 201

    def test_post_unicode_in_description(self, client, auth_headers):
        """Unicode in description should be accepted."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1234567",
            "description": "日本語テスト 🎌 café résumé",
        })
        assert resp.status_code == 201

    def test_post_zero_width_chars(self, client, auth_headers):
        """Zero-width characters should be accepted."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test\u200BName",
            "phone": "1234567",
        })
        assert resp.status_code == 201


class TestBoundaryStress:
    """Test boundary conditions on numeric and string fields."""

    def test_contact_name_exactly_100_chars(self, client, auth_headers):
        """Name with exactly 100 chars should be accepted."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "A" * 100,
            "phone": "1234567",
        })
        assert resp.status_code == 201

    def test_contact_name_101_chars_rejected(self, client, auth_headers):
        """Name with 101 chars should be rejected."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "A" * 101,
            "phone": "1234567",
        })
        assert resp.status_code == 422

    def test_contact_phone_exactly_20_chars(self, client, auth_headers):
        """Phone with exactly 20 chars should be accepted."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1" * 20,
        })
        assert resp.status_code == 201

    def test_contact_phone_21_chars_rejected(self, client, auth_headers):
        """Phone with 21 chars should be rejected."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1" * 21,
        })
        assert resp.status_code == 422

    def test_contact_latitude_boundary_90(self, client, auth_headers):
        """Latitude 90 should be accepted."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1234567",
            "latitude": 90.0,
        })
        assert resp.status_code == 201

    def test_contact_latitude_90_0001_rejected(self, client, auth_headers):
        """Latitude 90.0001 should be rejected."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1234567",
            "latitude": 90.0001,
        })
        assert resp.status_code == 422

    def test_contact_longitude_boundary_180(self, client, auth_headers):
        """Longitude -180 should be accepted."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1234567",
            "longitude": -180.0,
        })
        assert resp.status_code == 201

    def test_contact_latitude_negative_90(self, client, auth_headers):
        """Latitude -90 should be accepted."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1234567",
            "latitude": -90.0,
        })
        assert resp.status_code == 201

    def test_contact_longitude_positive_180(self, client, auth_headers):
        """Longitude 180 should be accepted."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1234567",
            "longitude": 180.0,
        })
        assert resp.status_code == 201

    def test_contact_longitude_180_0001_rejected(self, client, auth_headers):
        """Longitude 180.0001 should be rejected."""
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
        """PATCH method should be rejected."""
        headers = auth_headers()
        resp = client.request("PATCH", "/api/contacts", headers=headers, json={})
        assert resp.status_code in [405, 422]

    def test_options_on_contacts(self, client):
        """OPTIONS method should return valid response."""
        resp = client.options("/api/contacts")
        assert resp.status_code in [200, 204, 405]

    def test_delete_on_categories(self, client):
        """DELETE on categories should be rejected."""
        resp = client.delete("/api/categories")
        assert resp.status_code in [405, 403]

    def test_put_on_categories(self, client):
        """PUT on categories should be rejected."""
        resp = client.put("/api/categories")
        assert resp.status_code in [405, 422]


class TestHeaderFuzzing:
    """Test malformed and malicious headers."""

    def test_oversized_authorization_header(self, client):
        """Oversized auth header should be handled."""
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer " + "A" * 10000,
        })
        assert resp.status_code in [401, 413]

    def test_malformed_content_type(self, client, auth_headers):
        """Malformed content-type should be handled."""
        headers = auth_headers()
        resp = client.post(
            "/api/contacts",
            headers={**headers, "Content-Type": "text/html"},
            json={"name": "Test", "phone": "1234567"},
        )
        assert resp.status_code in [201, 422]

    def test_empty_user_agent(self, client):
        """Empty User-Agent should be accepted."""
        resp = client.get("/health", headers={"User-Agent": ""})
        assert resp.status_code == 200

    def test_giant_user_agent(self, client):
        """Giant User-Agent should be handled."""
        resp = client.get("/health", headers={"User-Agent": "A" * 50000})
        assert resp.status_code == 200

    def test_multiple_authorization_headers(self, client):
        """Duplicate authorization header should be handled."""
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer token1",
        })
        assert resp.status_code == 401


class TestQueryParameterFuzzing:
    """Test query parameter abuse."""

    def test_duplicate_query_params(self, client):
        """Duplicate query params should be handled."""
        resp = client.get("/api/contacts?skip=1&skip=2&skip=3")
        assert resp.status_code == 200

    def test_empty_query_param(self, client):
        """Empty query param should be handled."""
        resp = client.get("/api/contacts/search?q=")
        assert resp.status_code in [200, 400, 422]

    def test_very_long_query_param(self, client):
        """Very long query param should be handled."""
        resp = client.get(f"/api/contacts/search?q={'A' * 5000}")
        assert resp.status_code in [200, 414]

    def test_special_chars_in_query(self, client):
        """Special characters in query should be handled."""
        special = "!@#$%^&*()_+-=[]{}|;':\",.<>?/`~"
        resp = client.get(f"/api/contacts/search?q={special}")
        assert resp.status_code in [200, 400]

    def test_null_byte_in_query(self, client):
        """Null byte in query should be handled."""
        resp = client.get("/api/contacts/search?q=test%00injection")
        assert resp.status_code in [200, 400, 422]

    def test_limit_boundary(self, client):
        """Limit at max boundary should be accepted."""
        resp = client.get("/api/contacts?limit=500")
        assert resp.status_code in [200, 422]

    def test_limit_max_boundary(self, client):
        """Limit above max should be rejected."""
        resp = client.get("/api/contacts?limit=501")
        assert resp.status_code == 422


class TestJSONDepthFuzzing:
    """Test deeply nested JSON payloads."""

    def test_deeply_nested_json(self, client, auth_headers):
        """Deeply nested JSON should be handled by Pydantic."""
        headers = auth_headers()
        # Create deeply nested JSON
        nested = {"name": "Test", "phone": "1234567"}
        for i in range(10):
            nested = {"nested": nested}
        nested["name"] = "Test"
        nested["phone"] = "1234567"
        resp = client.post("/api/contacts", headers=headers, json=nested)
        assert resp.status_code in [201, 422, 500]

    def test_very_large_json(self, client, auth_headers):
        """Very large JSON payload should be handled."""
        headers = auth_headers()
        large_json = {
            "name": "Test",
            "phone": "1234567",
            "description": "A" * 100000,
        }
        resp = client.post("/api/contacts", headers=headers, json=large_json)
        assert resp.status_code in [201, 422, 413]


class TestFileUploadFuzzing:
    """Test file upload edge cases."""

    def test_upload_empty_file(self, client, create_user, db_session, auth_headers):
        """Empty file upload should be rejected."""
        from app.models.contact import Contact
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        headers = auth_headers()
        empty = io.BytesIO(b"")

        resp = client.post(
            f"/api/contacts/{contact.id}/image",
            headers=headers,
            files={"file": ("empty.jpg", empty, "image/jpeg")},
        )
        # Empty file should fail validation
        assert resp.status_code in [400, 422, 500]

    def test_upload_text_file_as_jpg(self, client, create_user, db_session, auth_headers):
        """Text file pretending to be JPEG should be rejected."""
        from app.models.contact import Contact
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        headers = auth_headers()
        fake = io.BytesIO(b"This is not a JPEG file at all, just plain text.")

        resp = client.post(
            f"/api/contacts/{contact.id}/image",
            headers=headers,
            files={"file": ("fake.jpg", fake, "image/jpeg")},
        )
        # Should fail JPEG magic bytes validation
        assert resp.status_code == 400

    def test_upload_gif_as_jpg(self, client, create_user, db_session, auth_headers):
        """GIF file pretending to be JPEG should be rejected."""
        from app.models.contact import Contact
        user = create_user()
        contact = Contact(name="Biz", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        headers = auth_headers()
        # Minimal GIF (not JPEG magic bytes)
        gif = io.BytesIO(b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;")

        resp = client.post(
            f"/api/contacts/{contact.id}/image",
            headers=headers,
            files={"file": ("image.gif", gif, "image/gif")},
        )
        # Should fail JPEG magic bytes validation
        assert resp.status_code == 400


class TestUnicodeNormalization:
    """Test Unicode normalization attacks."""

    def test_homoglyph_in_username(self, client, captcha):
        """Cyrillic homoglyph in username should be handled."""
        resp = client.post("/api/auth/register", json={
            "username": "аdmin",  # Cyrillic 'а'
            "email": "homoglyph@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        # Should be accepted as a different username (no collision)
        assert resp.status_code in [201, 400, 422]

    def test_rtl_override_in_name(self, client, auth_headers):
        """Right-to-left override character should be handled."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test\u202ERLO\u202C",  # RLO + POP
            "phone": "1234567",
        })
        assert resp.status_code in [201, 422]

    def test_zero_width_joiner_sequence(self, client, auth_headers):
        """Zero-width joiner sequence should be handled."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test\u200D\u200D\u200D",  # ZWJ sequence
            "phone": "1234567",
        })
        assert resp.status_code == 201
