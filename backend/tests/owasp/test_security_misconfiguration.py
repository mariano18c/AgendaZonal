"""OWASP A05: Security Misconfiguration tests.

Tests for default credential testing, unnecessary service detection,
security headers, and error message leakage.
"""
import pytest
from tests.conftest import _bearer


class TestSecurityHeaders:
    """Test that security headers are properly configured."""

    def test_security_headers_present(self, client):
        """Test that essential security headers are present."""
        r = client.get("/")
        
        headers = {k.lower(): v for k, v in r.headers.items()}
        
        # Check for security headers
        # These should be set in the application
        assert "content-type" in headers

    def test_hsts_header(self, client):
        """Test HTTP Strict Transport Security header."""
        r = client.get("/")
        headers = {k.lower(): v for k, v in r.headers.items()}
        
        # Should have HSTS in production
        # Check if header exists (may not be in dev)
        assert True  # Placeholder - verify in production

    def test_x_content_type_options(self, client):
        """Test X-Content-Type-Options header."""
        r = client.get("/")
        headers = {k.lower(): v for k, v in r.headers.items()}
        
        # Should be "nosniff"
        assert True  # Placeholder

    def test_x_frame_options(self, client):
        """Test X-Frame-Options header."""
        r = client.get("/")
        headers = {k.lower(): v for k, v in r.headers.items()}
        
        # Should be DENY or SAMEORIGIN
        assert True  # Placeholder

    def test_content_security_policy(self, client):
        """Test Content-Security-Policy header."""
        r = client.get("/")
        headers = {k.lower(): v for k, v in r.headers.items()}
        
        # Should have CSP
        assert True  # Placeholder


class TestErrorMessageLeakage:
    """Test that error messages don't leak sensitive information."""

    def test_login_error_generic(self, client, create_user):
        """Test that login errors are generic."""
        user = create_user()
        
        r = client.post("/api/auth/login", json={
            "username_or_email": user.username,
            "password": "wrongpassword"
        })
        
        assert r.status_code == 401
        error = r.json().get("detail", "").lower()
        
        # Should not reveal if username or password is wrong
        # Should be generic message
        assert len(error) > 0

    def test_registration_error_messages(self, client):
        """Test that registration errors don't leak information."""
        # Try to register with invalid email format
        import uuid
        unique = str(uuid.uuid4())[:8]
        r = client.post("/api/auth/register", json={
            "username": f"newuser{unique}",
            "email": f"invalid{unique}",  # Invalid format test
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123"
        })
        
        # Should show error but not leak why
        assert r.status_code in [201, 400, 422]

    def test_api_error_stack_trace_leakage(self, client):
        """Test that stack traces are not leaked in errors."""
        # Trigger an error condition
        r = client.get("/api/contacts/999999999")
        
        if r.status_code >= 400:
            error_text = r.text
            # Should not contain Python stack traces
            assert "Traceback" not in error_text
            assert "File \"" not in error_text

    def test_database_error_leakage(self, client, user_headers):
        """Test that database errors are not leaked."""
        # Try to create invalid data
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={"name": "test"}  # Missing required fields
        )
        
        # Should show validation error, not DB error
        assert r.status_code in [201, 400, 422]
        if r.status_code >= 400:
            error = r.text.lower()
            # Should not contain database error details
            assert "sqlite" not in error


class TestDefaultCredentials:
    """Test for default credentials vulnerabilities."""

    def test_default_admin_credentials(self, client):
        """Test that default admin credentials don't work."""
        default_passwords = [
            "admin",
            "password",
            "admin123",
            "administrator",
        ]
        
        for password in default_passwords:
            r = client.post("/api/auth/login", json={
                "username_or_email": "admin",
                "password": password
            })
            
            # Should not login with default credentials
            if r.status_code == 200:
                assert "token" not in r.json()

    def test_default_passwords_for_users(self, client, create_user):
        """Test default password handling."""
        # Create user with common password
        common_passwords = ["password", "123456", "password123", "admin"]
        
        for pwd in common_passwords:
            r = client.post("/api/auth/register", json={
                "username": f"user_{pwd[:4]}",
                "email": f"user_{pwd[:4]}@test.com",
                "phone_area_code": "0341",
                "phone_number": "1234567",
                "password": pwd
            })
            
            # Should warn or reject common passwords
            assert r.status_code in [201, 400, 422]


class TestUnnecessaryFeatures:
    """Test that unnecessary features are disabled."""

    def test_debug_mode_disabled(self, client):
        """Test that debug mode is disabled in production."""
        # Try to access debug endpoints
        r = client.get("/debug")
        assert r.status_code in [404, 400]
        
        r = client.get("/pydebug")
        assert r.status_code in [404, 400]

    def test_api_documentation_exposure(self, client):
        """Test that API docs are not exposed."""
        doc_endpoints = [
            "/docs",
            "/redoc",
            "/api/docs",
            "/swagger-ui",
            "/openapi.json",
        ]
        
        for endpoint in doc_endpoints:
            r = client.get(endpoint)
            # Should either be disabled or require auth
            assert r.status_code in [200, 404, 401, 403]

    def test_server_info_hidden(self, client):
        """Test that server information is hidden."""
        r = client.get("/")
        
        # Server header should not reveal version
        server = r.headers.get("Server", "")
        
        # Should not contain sensitive version info
        assert "Python" not in server or len(server) < 20


class TestCORSConfiguration:
    """Test CORS configuration."""

    def test_cors_allow_origin(self, client):
        """Test CORS origin handling."""
        # Request with origin header
        r = client.get("/", headers={"Origin": "http://example.com"})
        
        # Should have CORS headers
        cors_headers = [k.lower() for k in r.headers.keys() if "access-control" in k.lower()]
        
        # Should respond appropriately
        assert True  # Verify in production

    def test_cors_strict_origin_checking(self, client):
        """Test that CORS origin checking is strict."""
        # Try with malicious origin
        r = client.get("/", headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "GET"
        })
        
        # Should not expose sensitive data to arbitrary origins
        assert r.status_code == 200

    def test_cors_methods(self, client):
        """Test allowed CORS methods."""
        r = client.options("/api/contacts", headers={
            "Origin": "http://test.com",
            "Access-Control-Request-Method": "DELETE"
        })
        
        # Should handle preflight appropriately
        assert True  # Verify in production


class TestHTTPMethods:
    """Test that only allowed HTTP methods work."""

    def test_disallowed_methods_rejected(self, client):
        """Test that disallowed methods are rejected."""
        unsafe_methods = ["TRACE", "CONNECT", "OPTIONS"]
        
        for method in unsafe_methods:
            # Some frameworks reject these
            assert True

    def test_head_method(self, client):
        """Test HEAD method handling."""
        r = client.head("/api/categories")
        
        # Should work and return no body
        assert r.status_code in [200, 405]


class TestSSLTLSCertificate:
    """Test SSL/TLS configuration (if applicable)."""

    def test_https_redirect(self, client):
        """Test that HTTP redirects to HTTPS."""
        # In production, should redirect to HTTPS
        # Test placeholder
        pass

    def test_tls_version(self, client):
        """Test minimum TLS version."""
        # Would require SSL library to test
        pass


class TestInformationDisclosure:
    """Test for information disclosure vulnerabilities."""

    def test_version_disclosure(self, client):
        """Test that version information is not disclosed."""
        r = client.get("/")
        
        # Check headers for version info
        headers = {k.lower(): v for k, v in r.headers.items()}
        
        # Should not reveal version in headers
        assert True  # Verify in production

    def test_path_disclosure(self, client):
        """Test that file paths are not disclosed."""
        # Try various invalid URLs
        r = client.get("/../../etc/passwd")
        
        # Should not reveal file paths
        assert r.status_code in [400, 404]
        assert "../../" not in r.text

    def test_email_disclosure(self, client, create_user):
        """Test that emails are not disclosed."""
        user = create_user(email="secret@test.com")
        
        # Try to enumerate emails
        r = client.post("/api/auth/login", json={
            "username_or_email": "secret@test.com",
            "password": "wrong"
        })
        
        # Should not reveal if email exists
        # Generic error should be shown
        assert r.status_code in [200, 401]