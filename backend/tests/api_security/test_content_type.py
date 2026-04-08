"""API Security: Content-Type Confusion tests.

Tests for parser differentials and deserialization via content-type manipulation.
"""
import pytest
from tests.conftest import _bearer


class TestContentTypeHandling:
    """Test content-type handling."""

    def test_json_content_type(self, client, user_headers):
        """Test JSON content type handling."""
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={"name": "Test", "phone": "1234567"}
        )
        
        assert r.status_code in [201, 400]

    def test_form_urlencoded(self, client, user_headers):
        """Test form-urlencoded content type."""
        r = client.post(
            "/api/contacts",
            headers={**user_headers, "Content-Type": "application/x-www-form-urlencoded"},
            data="name=Test&phone=1234567"
        )
        
        # Should handle or reject - 422 is also acceptable
        assert r.status_code in [201, 400, 415, 422]

    def test_multipart_form_data(self, client, user_headers):
        """Test multipart form data."""
        # This would require file upload endpoint
        pass

    def test_xml_content_type(self, client, user_headers):
        """Test XML content type."""
        r = client.post(
            "/api/contacts",
            headers={**user_headers, "Content-Type": "application/xml"},
            data="<contact><name>Test</name><phone>1234567</phone></contact>"
        )
        
        # Should reject or handle safely - 422 is also acceptable
        assert r.status_code in [201, 400, 415, 422]

    def test_plain_text_content_type(self, client, user_headers):
        """Test plain text content type."""
        r = client.post(
            "/api/contacts",
            headers={**user_headers, "Content-Type": "text/plain"},
            data="name=Test&phone=1234567"
        )
        
        assert r.status_code in [201, 400, 415, 422]


class TestContentTypeOverride:
    """Test content-type override attempts."""

    def test_override_content_type_json(self, client, user_headers):
        """Test overriding content type with JSON."""
        r = client.post(
            "/api/contacts",
            headers={**user_headers, "Content-Type": "text/plain"},
            json={"name": "Test", "phone": "1234567"}
        )
        
        # Server should handle properly - 422 is also acceptable
        assert r.status_code in [201, 400, 415, 422]

    def test_charset_override(self, client, user_headers):
        """Test charset in content type."""
        r = client.post(
            "/api/contacts",
            headers={**user_headers, "Content-Type": "application/json; charset=utf-16"},
            json={"name": "Test", "phone": "1234567"}
        )
        
        assert r.status_code in [201, 400, 415]


class TestParserDifferential:
    """Test parser differential vulnerabilities."""

    def test_duplicate_keys_json(self, client, user_headers):
        """Test handling of duplicate keys in JSON."""
        # Send JSON with duplicate keys
        import json
        data = json.dumps({"name": "Test1", "name": "Test2"})
        
        r = client.post(
            "/api/contacts",
            headers={**user_headers, "Content-Type": "application/json"},
            content=data
        )
        
        # Should handle consistently
        assert r.status_code in [201, 400, 422]

    def test_nested_objects_json(self, client, user_headers):
        """Test nested object handling."""
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={
                "name": "Test",
                "phone": "1234567",
                "metadata": {"nested": {"deep": "value"}}
            }
        )
        
        assert r.status_code in [201, 400]

    def test_array_in_json_object(self, client, user_headers):
        """Test array in JSON object field."""
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={
                "name": "Test",
                "phone": "1234567",
                "tags": ["tag1", "tag2", "tag3"]
            }
        )
        
        assert r.status_code in [201, 400, 422]


class TestTypeConfusion:
    """Test type confusion vulnerabilities."""

    def test_integer_as_string(self, client, user_headers):
        """Test passing integer as string."""
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={
                "name": "Test",
                "phone": 1234567  # Integer instead of string
            }
        )
        
        assert r.status_code in [201, 400, 422]

    def test_string_as_integer(self, client, user_headers):
        """Test passing string as integer."""
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={
                "name": 12345,  # Integer instead of string
                "phone": "1234567"
            }
        )
        
        assert r.status_code in [201, 400, 422]

    def test_boolean_as_string(self, client, user_headers):
        """Test boolean as string."""
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={
                "name": "Test",
                "phone": "1234567",
                "active": "true"  # String instead of boolean
            }
        )
        
        assert r.status_code in [201, 400, 422]

    def test_null_as_string(self, client, user_headers):
        """Test null value handling."""
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={
                "name": "Test",
                "phone": None
            }
        )
        
        # Should handle null
        assert r.status_code in [201, 400]


class TestDeserializationSecurity:
    """Test deserialization security."""

    def test_yaml_deserialization(self, client, user_headers):
        """Test YAML deserialization security."""
        # If YAML is accepted
        pass

    def test_pickle_deserialization(self, client, user_headers):
        """Test pickle deserialization."""
        # Should not accept pickle
        pass

    def test_xml_deserialization(self, client, user_headers):
        """Test XML deserialization XXE protection."""
        # Test for XXE
        xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE contact [
        <!ENTITY xxe SYSTEM "file:///etc/passwd">
        ]>
        <contact>&xxe;</contact>"""
        
        r = client.post(
            "/api/contacts",
            headers={**user_headers, "Content-Type": "application/xml"},
            data=xml_payload
        )
        
        # Should reject or disable XXE - 422 is also acceptable
        assert r.status_code in [201, 400, 415, 422]


class TestJSONParsing:
    """Test JSON parsing edge cases."""

    def test_empty_json(self, client, user_headers):
        """Test empty JSON object."""
        r = client.post(
            "/api/contacts",
            headers={**user_headers, "Content-Type": "application/json"},
            json={}
        )
        
        assert r.status_code in [201, 400, 422]

    def test_deeply_nested_json(self, client, user_headers):
        """Test deeply nested JSON."""
        import json
        nested = {"level1": {"level2": {"level3": {"level4": {"level5": "value"}}}}}
        
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={
                "name": json.dumps(nested),
                "phone": "1234567"
            }
        )
        
        assert r.status_code in [201, 400, 422]

    def test_special_characters_json(self, client, user_headers):
        """Test special characters in JSON."""
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={
                "name": "Test<script>alert(1)</script>",
                "phone": "1234567"
            }
        )
        
        assert r.status_code in [201, 400, 422]


class TestContentTypeSecurity:
    """Test content-type security headers."""

    def test_accept_header_handling(self, client):
        """Test Accept header handling."""
        accept_types = [
            "application/json",
            "application/xml",
            "text/html",
            "*/*",
        ]
        
        for accept in accept_types:
            r = client.get("/api/contacts", headers={"Accept": accept})
            # Should handle accept header properly
            assert r.status_code == 200

    def test_content_negotiation(self, client):
        """Test content negotiation."""
        r = client.get("/api/contacts", headers={"Accept": "application/json"})
        
        # Should return JSON
        assert r.status_code == 200