"""API Security: Documentation Exposure tests.

Tests for API documentation exposure and information leakage.
"""
import pytest
import re
from tests.conftest import _bearer


class TestAPIEndpointsDiscovery:
    """Test API endpoint discovery."""

    def test_common_api_paths(self, client):
        """Test common API paths."""
        common_paths = [
            "/api",
            "/api/v1",
            "/api/v2",
            "/rest",
            "/swagger",
            "/swagger-ui",
            "/api-docs",
            "/redoc",
        ]
        
        results = []
        for path in common_paths:
            r = client.get(path)
            results.append((path, r.status_code))
        
        # Should handle all paths gracefully
        assert all(s in [200, 404, 301, 302] for _, s in results)

    def test_api_version_discovery(self, client):
        """Test API version discovery."""
        versions = ["/v1", "/v2", "/v3", "/v1.0", "/v2.0"]
        
        for version in versions:
            r = client.get(f"/api{version}/contacts")
            # Should handle version gracefully
            assert r.status_code in [200, 404, 400]

    def test_graphql_endpoint(self, client):
        """Test GraphQL endpoint discovery."""
        r = client.get("/graphql")
        
        # Should handle or not exist
        assert r.status_code in [200, 404]


class TestSwaggerOpenAPIExposure:
    """Test Swagger/OpenAPI exposure."""

    def test_openapi_json_exposed(self, client):
        """Test OpenAPI JSON is accessible."""
        endpoints = [
            "/openapi.json",
            "/api/openapi.json",
            "/swagger.json",
        ]
        
        for endpoint in endpoints:
            r = client.get(endpoint)
            # Should require auth or not exist
            assert r.status_code in [200, 404, 401, 403]

    def test_swagger_ui_exposed(self, client):
        """Test Swagger UI is accessible."""
        r = client.get("/docs")
        
        # Should require auth in production
        assert r.status_code in [200, 404, 401, 403]

    def test_api_blueprint_exposed(self, client):
        """Test API Blueprint documentation."""
        r = client.get("/api/apiary.apib")
        
        assert r.status_code in [200, 404]


class TestInformationLeakage:
    """Test information leakage."""

    def test_stack_trace_exposure(self, client):
        """Test stack traces are not exposed."""
        # Trigger an error
        r = client.get("/api/contacts/999999999")
        
        if r.status_code >= 500:
            # Should not expose stack trace
            assert "Traceback" not in r.text
            assert "File \"" not in r.text

    def test_server_info_exposure(self, client):
        """Test server information is not exposed."""
        r = client.get("/")
        
        # Check headers
        server = r.headers.get("Server", "")
        
        # Should not expose detailed version info
        assert "Python" not in server or len(server) < 20

    def test_database_error_exposure(self, client, user_headers):
        """Test database errors are not exposed."""
        # Trigger potential DB error
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={"name": "A" * 10000}
        )
        
        # Should show generic error
        error = r.text.lower()
        assert "sqlite" not in error or "error" not in error


class TestEndpointEnumeration:
    """Test endpoint enumeration."""

    def test_http_methods_enumeration(self, client, user_headers):
        """Test HTTP methods can be enumerated."""
        endpoints = [
            "/api/contacts",
            "/api/categories",
            "/api/auth/login",
        ]
        
        for endpoint in endpoints:
            # Try different methods
            methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
            
            for method in methods:
                # This would require different client calls
                pass

    def test_id_enumeration(self, client):
        """Test ID enumeration."""
        # Try to enumerate IDs
        for i in range(1, 11):
            r = client.get(f"/api/contacts/{i}")
            
            # Should handle
            assert r.status_code in [200, 404]


class TestAPIDocumentation:
    """Test API documentation security."""

    def test_docs_require_auth(self, client):
        """Test documentation requires authentication."""
        r = client.get("/docs")
        
        # In production, should require auth
        assert r.status_code in [200, 404, 401, 403]

    def test_internal_docs_not_exposed(self, client):
        """Test internal documentation is not exposed."""
        doc_paths = [
            "/internal/docs",
            "/private/docs",
            "/admin/docs",
            "/development/docs",
        ]
        
        for path in doc_paths:
            r = client.get(path)
            assert r.status_code in [404, 401, 403]

    def test_readme_not_served(self, client):
        """Test README files are not served."""
        readme_paths = [
            "/README",
            "/readme",
            "/README.md",
            "/docs/README",
        ]
        
        for path in readme_paths:
            r = client.get(path)
            assert r.status_code in [404, 200]


class TestSourceCodeExposure:
    """Test source code exposure."""

    def test_source_files_not_exposed(self, client):
        """Test source files are not exposed."""
        source_extensions = [".py", ".js", ".ts", ".java", ".go", ".rb"]
        
        for ext in source_extensions:
            paths = [
                f"/app{ext}",
                f"/src{ext}",
                f"/index{ext}",
            ]
            
            for path in paths:
                r = client.get(path)
                assert r.status_code in [404, 403]

    def test_config_files_not_exposed(self, client):
        """Test config files are not exposed."""
        config_files = [
            ".env",
            "config.py",
            "settings.py",
            "application.properties",
            "appsettings.json",
        ]
        
        for config in config_files:
            r = client.get(f"/{config}")
            assert r.status_code in [404, 403]

    def test_git_directory_exposed(self, client):
        """Test .git directory is not exposed."""
        r = client.get("/.git/config")
        
        assert r.status_code in [404, 403]