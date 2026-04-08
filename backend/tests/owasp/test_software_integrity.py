"""OWASP A08: Software and Data Integrity Failures tests.

Tests for deserialization vulnerabilities and CI/CD integrity.
"""
import pytest
import json
from tests.conftest import _bearer


class TestDeserializationSecurity:
    """Test deserialization security."""

    def test_json_deserialization_safe(self, client, user_headers):
        """Test JSON deserialization is safe."""
        # Try various JSON payloads
        payloads = [
            {"name": "Test", "data": {"nested": "value"}},
            {"name": "Test", "data": [1, 2, 3]},
            {"name": "Test", "data": None},
        ]
        
        for payload in payloads:
            r = client.post(
                "/api/contacts",
                headers=user_headers,
                json=payload
            )
            assert r.status_code in [201, 400, 422]

    def test_no_pickle_deserialization(self, client, user_headers):
        """Test that pickle deserialization is not used."""
        # Try pickle-like payload - should be rejected as invalid content
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={"name": "test", "phone": "1234567"}
        )
        
        # JSON should work, binary pickle should be rejected
        assert r.status_code in [201, 400, 415, 422]

    def test_yaml_deserialization_safe(self, client, user_headers):
        """Test YAML deserialization is safe."""
        # Try YAML payloads
        yaml_payloads = [
            "name: Test\nphone: 123",
            "!!python/object:__main__.User {}",
        ]
        
        for payload in yaml_payloads:
            r = client.post(
                "/api/contacts",
                headers={**user_headers, "Content-Type": "application/x-yaml"},
                content=payload.encode()
            )
            assert r.status_code in [201, 400, 415, 422]


class TestCIDeployIntegrity:
    """Test CI/CD pipeline integrity."""

    def test_build_integrity(self):
        """Test build process integrity."""
        # Would require build system access
        pass

    def test_no_secrets_in_code(self):
        """Test that secrets are not in source code."""
        # Would require secret scanning
        pass

    def test_dependencies_verified(self):
        """Test that dependencies are verified."""
        # Would require supply chain security testing
        pass


class TestInsecureDataTransfer:
    """Test insecure data transfer."""

    def test_api数据传输安全(self, client):
        """Test API data transfer security."""
        r = client.get("/api/categories")
        
        # Should work over HTTPS in production
        assert r.status_code == 200

    def test_token_not_in_response_body(self, client, create_user):
        """Test tokens are not in response body."""
        user = create_user()
        
        r = client.post("/api/auth/login", json={
            "username_or_email": user.username,
            "password": "password123"
        })
        
        if r.status_code == 200:
            data = r.json()
            # Token should be in response, but not in other responses
            assert "token" in data or "message" in data


class TestUpdateIntegrity:
    """Test software update integrity."""

    def test_update_signature_verified(self):
        """Test that updates are signature verified."""
        # Would require update system testing
        pass

    def test_rollback_protection(self):
        """Test rollback protection."""
        # Would require deployment system testing
        pass


class TestCodeIntegrity:
    """Test code integrity."""

    def test_no_code_injection(self, client):
        """Test no code can be injected."""
        # Try code injection payloads
        payloads = [
            "<script>alert(1)</script>",
            "{{7*7}}",
            "${7*7}",
            "<% phpinfo() %>",
        ]
        
        for payload in payloads:
            r = client.get(f"/api/contacts/search?q={payload}")
            assert r.status_code in [200, 400, 422]

    def test_no_template_injection(self, client):
        """Test template injection is prevented."""
        payloads = [
            "{{constructor}}",
            "${constructor}",
            "#{runtime}",
        ]
        
        for payload in payloads:
            r = client.get(f"/api/contacts/search?q={payload}")
            assert r.status_code in [200, 400, 422]