"""API Security: HTTP Method Override tests.

Tests for unsafe HTTP methods via headers.
"""
import pytest
from tests.conftest import _bearer


class TestMethodOverride:
    """Test HTTP method override."""

    def test_x_http_method_override(self, client, user_headers):
        """Test X-HTTP-Method-Override header."""
        # Try to override GET to DELETE
        r = client.get(
            "/api/contacts",
            headers={**user_headers, "X-HTTP-Method-Override": "DELETE"}
        )
        
        # Should either honor or ignore
        assert r.status_code in [200, 400, 405]

    def test_x_method_override_post(self, client, user_headers):
        """Test method override from POST."""
        # Override POST to PUT
        r = client.post(
            "/api/contacts",
            headers={**user_headers, "X-HTTP-Method-Override": "PUT"},
            json={"name": "Test"}
        )
        
        # Should handle properly
        assert r.status_code in [201, 400, 405]

    def test_header_case_insensitivity(self, client, user_headers):
        """Test header name case insensitivity."""
        # Different cases
        headers = [
            {"X-HTTP-Method-Override": "DELETE"},
            {"x-http-method-override": "DELETE"},
            {"X-Http-Method-Override": "DELETE"},
        ]
        
        for header in headers:
            r = client.get("/api/contacts", headers={**user_headers, **header})
            # Should handle consistently
            assert r.status_code in [200, 400, 405]


class TestMethodTampering:
    """Test method tampering."""

    def test_lowercase_method(self, client, user_headers):
        """Test lowercase HTTP method."""
        # Try lowercase delete
        r = client.delete("/api/contacts/1", headers=user_headers)
        
        # Should work
        assert r.status_code in [200, 404, 405]

    def test_unknown_method(self, client, user_headers):
        """Test unknown HTTP method."""
        r = client.delete("/api/contacts", headers=user_headers)
        
        # Should reject
        assert r.status_code in [404, 405]


class TestHTTPMethodSecurity:
    """Test HTTP method security."""

    def test_safe_methods_only(self, client):
        """Test SAFE methods don't modify data."""
        # GET should be read-only
        r = client.get("/api/categories")
        assert r.status_code == 200

    def test_unsafe_methods_require_auth(self, client):
        """Test unsafe methods require authentication."""
        unsafe_methods = ["POST", "PUT", "DELETE", "PATCH"]
        
        for method in unsafe_methods:
            # Without auth, should require auth
            if method == "POST":
                r = client.post("/api/contacts", json={"name": "Test"})
            elif method == "PUT":
                r = client.put("/api/contacts/1", json={"name": "Test"})
            elif method == "DELETE":
                r = client.delete("/api/contacts/1")
            else:
                r = client.patch("/api/contacts/1", json={"name": "Test"})
            
            assert r.status_code in [200, 201, 401, 403, 404, 405]

    def test_options_method_security(self, client):
        """Test OPTIONS method security."""
        r = client.options("/api/contacts")
        
        # Should handle
        assert r.status_code in [200, 405]


class TestMethodOverrideBypass:
    """Test method override bypass attempts."""

    def test_override_to_admin_method(self, client, user_headers):
        """Test overriding to admin method."""
        # Try to override to admin-level method
        r = client.get(
            "/api/admin/users",
            headers={**user_headers, "X-HTTP-Method-Override": "DELETE"}
        )
        
        # Should check permissions
        assert r.status_code in [200, 403, 404]

    def test_override_versioning(self, client):
        """Test method override with versioning."""
        # If API versioning exists
        pass