"""Fuzzing: Web Fuzzing tests.

Tests for OWASP ZAP integration and web fuzzing.
"""
import pytest
import random
import string


class TestWebFuzzing:
    """Web fuzzing tests."""

    def test_fuzz_all_endpoints(self, client):
        """Test fuzzing all endpoints."""
        endpoints = [
            "/",
            "/api/contacts",
            "/api/categories",
            "/search",
            "/login",
            "/register",
        ]
        
        for endpoint in endpoints:
            # Fuzz with random data
            fuzz = ''.join(random.choices(string.ascii_letters, k=50))
            r = client.get(f"{endpoint}?q={fuzz}")
            
            # Accept 405 for method not allowed
            assert r.status_code in [200, 400, 404, 405, 422]

    def test_fuzz_query_parameters(self, client):
        """Test fuzzing query parameters."""
        params = ["q", "search", "query", "term", "filter"]
        
        for param in params:
            fuzz = ''.join(random.choices(string.ascii_letters + string.digits, k=100))
            r = client.get(f"/api/contacts/search?{param}={fuzz}")
            
            assert r.status_code in [200, 400, 422]

    def test_fuzz_headers(self, client):
        """Test fuzzing HTTP headers."""
        fuzz_headers = [
            {"X-Custom-Header": ''.join(random.choices(string.ascii_letters, k=50))},
            {"X-Forwarded-For": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"},
            {"X-Real-IP": f"192.168.{random.randint(1,255)}.{random.randint(1,255)}"},
        ]
        
        for headers in fuzz_headers:
            r = client.get("/api/categories", headers=headers)
            assert r.status_code == 200


class TestPathFuzzing:
    """Path fuzzing tests."""

    def test_common_paths(self, client):
        """Test common paths."""
        common_paths = [
            "/admin", "/administrator", "/backup", "/backup.zip",
            "/config", "/config.php", "/.git/config", "/.env",
            "/debug", "/phpinfo", "/server-status", "/status",
        ]
        
        for path in common_paths:
            r = client.get(path)
            assert r.status_code in [200, 301, 302, 404, 403]

    def test_path_traversal_fuzz(self, client):
        """Test path traversal fuzzing."""
        traversal_payloads = [
            "../",
            "../../",
            "../../../",
            "..\\..\\..\\",
            "%2e%2e/",
            "%2e%2e%2f",
            "....//",
            "..%252f",
        ]
        
        for payload in traversal_payloads:
            r = client.get(f"/api/contacts/{payload}")
            # Accept 422 for path parameters
            assert r.status_code in [200, 400, 404, 422]


class TestParameterFuzzing:
    """Parameter fuzzing tests."""

    def test_fuzz_pagination(self, client):
        """Test pagination fuzzing."""
        fuzz_values = [
            "-1", "0", "999999999", "abc", "1.5", "-1.5",
            "null", "none", "undefined", "NaN",
        ]
        
        for value in fuzz_values:
            r = client.get(f"/api/contacts?page={value}&limit={value}")
            assert r.status_code in [200, 400, 422]

    def test_fuzz_sort_parameter(self, client):
        """Test sort parameter fuzzing."""
        fuzz_values = [
            "name", "id", "created_at",
            "name;DROP TABLE", "name UNION SELECT",
            "1;DELETE FROM", "ASC;DROP",
        ]
        
        for value in fuzz_values:
            r = client.get(f"/api/contacts?sort={value}")
            assert r.status_code in [200, 400, 422]