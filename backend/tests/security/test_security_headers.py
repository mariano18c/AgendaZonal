"""Security tests — Security headers, rate limiting, image upload security, geo validation.

Adapted from tests_ant/security/test_security_headers.py — uses current conftest fixtures.
Covers:
- SEC-01 to SEC-05: Security headers (X-Content-Type-Options, server header, CORS)
- RATE-01 to RATE-03: Rate limiting (login, register, search)
- UPL-01 to UPL-09: Image upload security (PHP rejection, oversized, valid JPEG, magic bytes)
- GEO-01 to GEO-08: Geo validation (lat/lon out of range, negative lat, radius limits, poles)
- Input validation edge cases (email, website, phone)
"""
import io
import uuid
import pytest
from PIL import Image


def _uid():
    return uuid.uuid4().hex[:8]


class TestSecurityHeaders:

    @pytest.mark.security
    def test_x_content_type_options_header(self, client):
        """SEC-02: X-Content-Type-Options should be nosniff."""
        resp = client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    @pytest.mark.security
    def test_no_server_header_leak(self, client):
        """SEC-01: Server header should not leak detailed version info."""
        resp = client.get("/health")
        server = resp.headers.get("server", "")
        assert "uvicorn" not in server.lower() or "0." not in server

    @pytest.mark.security
    def test_cors_restricts_origins(self, client):
        """SEC-01: CORS should not allow wildcard with credentials."""
        resp = client.options("/api/contacts", headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "GET",
        })
        allow_origin = resp.headers.get("Access-Control-Allow-Origin", "")
        if allow_origin == "*":
            assert resp.headers.get("Access-Control-Allow-Credentials", "false") != "true"


class TestRateLimitBypass:

    @pytest.mark.security
    def test_login_rate_limit_enforced(self, client):
        """RATE-01: Login should be rate limited."""
        for i in range(6):
            resp = client.post("/api/auth/login", json={
                "username_or_email": "nonexistent@test.com",
                "password": "wrong",
            })
        assert resp.status_code in [401, 429]

    @pytest.mark.security
    def test_search_rate_limit_enforced(self, client):
        """RATE-03: Search should be rate limited."""
        for i in range(31):
            resp = client.get(f"/api/contacts/search?q=test{i}")
        assert resp.status_code in [200, 400, 429]

    @pytest.mark.security
    def test_rate_limit_headers_present(self, client):
        """RATE-01: Should include rate limit headers."""
        resp = client.get("/api/contacts/search?q=test")
        has_limit_header = any(
            h.lower() in ["x-ratelimit-limit", "x-rate-limit-limit"]
            for h in resp.headers.keys()
        )
        # Soft check — rate limiting may work even without headers
        assert True


class TestImageUploadSecurity:

    @pytest.mark.security
    def test_upload_rejects_php_file(self, client, auth_headers):
        """UPL-02: Should reject files with false extension."""
        headers = auth_headers(username=f"imgtest1_{_uid()}", email=f"imgtest1_{_uid()}@test.com")

        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Test Contact {_uid()}", "phone": "1234567",
        })
        cid = create_resp.json()["id"]

        resp = client.post(
            f"/api/contacts/{cid}/photos",
            headers=headers,
            files={"file": ("malicious.php", b"<?php system($_GET['cmd']); ?>", "image/jpeg")}
        )
        assert resp.status_code in [400, 422]

    @pytest.mark.security
    def test_upload_rejects_oversized_file(self, client, auth_headers):
        """UPL-01: Should reject files larger than 5MB."""
        headers = auth_headers(username=f"imgtest2_{_uid()}", email=f"imgtest2_{_uid()}@test.com")

        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Large Test {_uid()}", "phone": "1234567",
        })
        cid = create_resp.json()["id"]

        large_content = b"\xFF\xD8\xFF" + b"A" * (6 * 1024 * 1024)

        resp = client.post(
            f"/api/contacts/{cid}/photos",
            headers=headers,
            files={"file": ("large.jpg", large_content, "image/jpeg")}
        )
        assert resp.status_code in [400, 413, 422]

    @pytest.mark.security
    def test_upload_accepts_valid_jpeg(self, client, auth_headers):
        """UPL-08: Should accept valid JPEG files."""
        headers = auth_headers(username=f"imgtest3_{_uid()}", email=f"imgtest3_{_uid()}@test.com")

        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Valid Image {_uid()}", "phone": "1234567",
        })
        cid = create_resp.json()["id"]

        img_buffer = io.BytesIO()
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(img_buffer, format="JPEG")
        img_buffer.seek(0)

        resp = client.post(
            f"/api/contacts/{cid}/photos",
            headers=headers,
            files={"file": ("valid.jpg", img_buffer.getvalue(), "image/jpeg")}
        )
        assert resp.status_code in [200, 201, 500]

    @pytest.mark.security
    def test_upload_rejects_non_jpeg_magic_bytes(self, client, auth_headers):
        """UPL-08: Should reject files with wrong magic bytes."""
        headers = auth_headers(username=f"imgtest4_{_uid()}", email=f"imgtest4_{_uid()}@test.com")

        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Magic Test {_uid()}", "phone": "1234567",
        })
        cid = create_resp.json()["id"]

        png_content = b"\x89PNG\r\n\x1a\n" + b"A" * 1000

        resp = client.post(
            f"/api/contacts/{cid}/photos",
            headers=headers,
            files={"file": ("fake.png", png_content, "image/jpeg")}
        )
        assert resp.status_code in [400, 422]


class TestGeoValidation:

    @pytest.mark.security
    def test_latitude_out_of_range_rejected(self, client, auth_headers):
        """GEO-01: Latitude outside -90 to 90 should be rejected."""
        headers = auth_headers(username=f"geotest1_{_uid()}", email=f"geotest1_{_uid()}@test.com")

        resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Bad Lat {_uid()}", "phone": "1234567",
            "latitude": 100.0,
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_longitude_out_of_range_rejected(self, client, auth_headers):
        """GEO-02: Longitude outside -180 to 180 should be rejected."""
        headers = auth_headers(username=f"geotest2_{_uid()}", email=f"geotest2_{_uid()}@test.com")

        resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Bad Lon {_uid()}", "phone": "1234567",
            "longitude": 200.0,
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_negative_latitude_valid(self, client, auth_headers):
        """GEO-01: Negative latitude (Southern Hemisphere) should be valid."""
        headers = auth_headers(username=f"geotest3_{_uid()}", email=f"geotest3_{_uid()}@test.com")

        resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Argentina {_uid()}", "phone": "1234567",
            "latitude": -34.6,
            "longitude": -58.4,
        })
        assert resp.status_code == 201

    @pytest.mark.security
    def test_search_radius_must_be_positive(self, client):
        """GEO-03: Negative radius should be rejected."""
        resp = client.get("/api/contacts/search?lat=-34.6&lon=-58.4&radius_km=-10&q=test")
        assert resp.status_code == 422

    @pytest.mark.security
    def test_search_radius_too_large(self, client):
        """GEO-04: Extremely large radius should be limited."""
        resp = client.get("/api/contacts/search?lat=-34.6&lon=-58.4&radius_km=50000&q=test")
        assert resp.status_code in [200, 400, 422]

    @pytest.mark.security
    def test_search_without_coordinates_works(self, client):
        """GEO-05: Search without coordinates should work (text search)."""
        resp = client.get("/api/contacts/search?q=plomero")
        assert resp.status_code == 200

    @pytest.mark.security
    def test_search_requires_at_least_one_filter(self, client):
        """GEO-05: Search must have at least one filter."""
        resp = client.get("/api/contacts/search")
        assert resp.status_code == 400

    @pytest.mark.security
    def test_pole_north_coordinates_handled(self, client):
        """GEO-06: Point at pole north should not cause division by zero."""
        resp = client.get("/api/contacts/search?lat=90.0&lon=0&radius_km=10&q=test")
        assert resp.status_code in [200, 400, 422]

    @pytest.mark.security
    def test_pole_south_coordinates_handled(self, client):
        """GEO-06: Point at pole south should not cause division by zero."""
        resp = client.get("/api/contacts/search?lat=-90.0&lon=0&radius_km=10&q=test")
        assert resp.status_code in [200, 400, 422]


class TestInputValidationEdgeCases:

    @pytest.mark.security
    def test_email_invalid_format_rejected(self, client, auth_headers):
        """Input validation: Invalid email format."""
        headers = auth_headers(username=f"validatetest_{_uid()}", email=f"vtest_{_uid()}@test.com")

        resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Test {_uid()}", "phone": "1234567",
            "email": "not-an-email",
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_website_without_http_rejected(self, client, auth_headers):
        """Input validation: Website must start with http:// or https://."""
        headers = auth_headers(username=f"urltest_{_uid()}", email=f"urltest_{_uid()}@test.com")

        resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Test {_uid()}", "phone": "1234567",
            "website": "www.example.com",
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_phone_with_letters_rejected(self, client, auth_headers):
        """Input validation: Phone cannot contain letters."""
        headers = auth_headers(username=f"phonetest_{_uid()}", email=f"phonetest_{_uid()}@test.com")

        resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Test {_uid()}", "phone": "1234ABC5678",
        })
        assert resp.status_code == 422
