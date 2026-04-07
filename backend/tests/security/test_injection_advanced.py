"""Security tests — Advanced injection attacks. Merged from tests_ant."""


class TestInjectionAttacks:
    """Advanced injection attacks beyond basic SQLi."""

    def test_sqlite_pragma_injection(self, client):
        """Attempt to modify SQLite PRAGMAs via search."""
        payloads = [
            "'; PRAGMA journal_mode=DELETE; --",
            "'; PRAGMA foreign_keys=OFF; --",
            "' UNION SELECT sql FROM sqlite_master; --",
        ]
        for payload in payloads:
            resp = client.get(f"/api/contacts/search?q={payload}")
            assert resp.status_code == 200
            for item in resp.json():
                assert "CREATE TABLE" not in str(item)

    def test_header_injection(self, client):
        """Attempt header injection via CRLF."""
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer token\r\nX-Injected: true",
        })
        assert resp.status_code == 401

    def test_json_type_confusion(self, client, auth_headers):
        """Send array instead of object in JSON body."""
        headers = auth_headers(username="type_conf", email="type_conf@test.com")
        resp = client.post("/api/contacts", headers=headers, content=b"[]")
        assert resp.status_code == 422

    def test_multipart_injection(self, client, auth_headers):
        """Malformed multipart data should be handled gracefully."""
        headers = auth_headers(username="multipart_inj", email="multipart_inj@test.com")
        resp = client.post(
            "/api/contacts",
            headers={**headers, "Content-Type": "multipart/form-data; boundary=----WebKit"},
            content=b"------WebKit\r\ninvalid\r\n------WebKit--",
        )
        assert resp.status_code in [400, 422, 201]

    def test_path_traversal_in_static(self, client):
        """Path traversal in static file serving."""
        resp = client.get("/js/../../etc/passwd")
        assert resp.status_code in [404, 403]

    def test_null_byte_injection(self, client):
        """Null byte in URL should be handled."""
        resp = client.get("/api/contacts/search?q=test%00injection")
        assert resp.status_code in [200, 400]

    def test_unicode_normalization_attack(self, client, auth_headers):
        """Unicode homoglyph attack in username."""
        import uuid
        uid = uuid.uuid4().hex[:8]
        headers = auth_headers(username="admіn", email=f"homoglyph_{uid}@test.com")  # і = Cyrillic
        resp = client.get("/api/users", headers=headers)
        assert resp.status_code in [403, 401]
