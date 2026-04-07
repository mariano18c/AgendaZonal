"""Security tests — Information disclosure. Merged from tests_ant."""


class TestInformationDisclosure:
    """Attempt to extract sensitive information from error responses."""

    def test_no_stack_trace_on_500(self, client, auth_headers):
        """Error responses should not contain stack traces."""
        headers = auth_headers(username="info_disc", email="info_disc@test.com")
        resp = client.post(
            "/api/contacts",
            headers=headers,
            content=b"not valid json {{{",
        )
        text = resp.text.lower()
        assert "traceback" not in text
        assert "file \"" not in text
        assert "line " not in text
        assert "sqlalchemy" not in text

    def test_no_db_path_in_errors(self, client):
        """Error responses should not reveal database paths."""
        resp = client.get("/api/contacts/invalid")
        text = resp.text.lower()
        assert "sqlite" not in text
        assert ".db" not in text
        assert "database" not in text

    def test_no_internal_paths_in_404(self, client):
        """404 responses should not reveal internal paths."""
        resp = client.get("/api/nonexistent/endpoint")
        text = resp.text.lower()
        assert "backend" not in text
        assert "app/" not in text
        assert "routes" not in text

    def test_security_headers_present(self, client):
        """All responses should have security headers."""
        resp = client.get("/")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert "Content-Security-Policy" in resp.headers
        assert "Referrer-Policy" in resp.headers

    def test_server_header_not_leaked(self, client):
        """Server header should not reveal framework/version."""
        resp = client.get("/health")
        server = resp.headers.get("server", "")
        assert "uvicorn" not in server.lower()
        assert "fastapi" not in server.lower()
        assert "python" not in server.lower()

    def test_rate_limit_headers_on_api(self, client):
        """API responses should include rate limit headers."""
        resp = client.get("/api/categories")
        assert "X-RateLimit-Limit" in resp.headers
        assert "X-RateLimit-Remaining" in resp.headers
        assert "X-RateLimit-Reset" in resp.headers
