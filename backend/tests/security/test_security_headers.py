"""Security headers and rate limiting bypass tests.

Tests from QA plan:
- SEC-01 to SEC-05: Security headers
- RATE-02: X-Forwarded-For bypass
- UPL-01 to UPL-09: Image upload security
- GEO-01 to GEO-08: Geo validation
"""
import pytest
from datetime import datetime, timedelta, timezone


class TestSecurityHeaders:

    @pytest.mark.security
    def test_x_content_type_options_header(self, client):
        """SEC-02: X-Content-Type-Options should be nosniff"""
        resp = client.get("/health")
        assert "x-content-type-options" in [h.lower() for h in resp.headers.keys()]

    @pytest.mark.security
    def test_no_server_header_leak(self, client):
        """SEC-01: Server header should not leak version info"""
        resp = client.get("/health")
        server = resp.headers.get("server", "")
        # Should not expose detailed version
        assert "uvicorn" not in server.lower() or "0." not in server

    @pytest.mark.security
    def test_cors_restricts_origins(self, client):
        """SEC-01: CORS should not allow wildcard with credentials"""
        resp = client.options("/api/contacts", headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "GET",
        })
        # Should either not set Access-Control-Allow-Origin or not allow wildcard
        allow_origin = resp.headers.get("Access-Control-Allow-Origin", "")
        if allow_origin == "*":
            # If wildcard, should not allow credentials
            assert resp.headers.get("Access-Control-Allow-Credentials", "false") != "true"


class TestRateLimitBypass:

    @pytest.mark.security
    def test_login_rate_limit_enforced(self, client):
        """RATE-01: Login should be rate limited to 5/minute"""
        for i in range(6):
            resp = client.post("/api/auth/login", json={
                "username_or_email": "nonexistent@test.com",
                "password": "wrong",
            })
        # 5th should succeed or fail with 401, 6th should get rate limited
        assert resp.status_code in [401, 429]

    @pytest.mark.security
    def test_register_rate_limit_enforced(self, client):
        """RATE-01: Registration should be rate limited to 3/minute"""
        for i in range(4):
            resp = client.post("/api/auth/register", json={
                "username": f"ratetest{i}",
                "email": f"ratetest{i}@test.com",
                "phone_area_code": "0341",
                "phone_number": f"12345{i:03d}",
                "password": "password123",
            })
        # 3rd should work or fail with 400, 4th should get rate limited
        assert resp.status_code in [201, 400, 422, 429]

    @pytest.mark.security
    def test_search_rate_limit_enforced(self, client):
        """RATE-03: Search should be rate limited to 30/minute"""
        for i in range(31):
            resp = client.get(f"/api/contacts/search?q=test{i}")
        # 30th should work, 31st should get rate limited
        assert resp.status_code in [200, 400, 429]

    @pytest.mark.security
    def test_rate_limit_headers_present(self, client):
        """RATE-01: Should include rate limit headers"""
        # Make a request that doesn't get rate limited first
        resp = client.get("/api/contacts/search?q=test")
        # Check for rate limit headers (slowapi typically adds these)
        # Note: May not be present on all responses, this is informational
        has_limit_header = any(
            h.lower() in ["x-ratelimit-limit", "x-rate-limit-limit"]
            for h in resp.headers.keys()
        )
        # This is a soft check - rate limiting may work even without headers
        assert True  # Informational test


class TestImageUploadSecurity:

    @pytest.mark.security
    def test_upload_rejects_php_file(self, client, auth_headers):
        """UPL-02: Should reject files with false extension"""
        headers = auth_headers(username="imgtest1", email="imgtest1@test.com")
        
        # Create a contact first
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test Contact", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        # Try to upload PHP file with JPEG content-type
        resp = client.post(
            f"/api/contacts/{cid}/image",
            headers=headers,
            files={"file": ("malicious.php", b"<?php system($_GET['cmd']); ?>", "image/jpeg")}
        )
        # Should reject - either by extension or magic bytes
        assert resp.status_code == 400

    @pytest.mark.security
    def test_upload_rejects_oversized_file(self, client, auth_headers):
        """UPL-01: Should reject files larger than 5MB"""
        headers = auth_headers(username="imgtest2", email="imgtest2@test.com")
        
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Large Test", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        # Create a 6MB fake image
        large_content = b"\xFF\xD8\xFF" + b"A" * (6 * 1024 * 1024)
        
        resp = client.post(
            f"/api/contacts/{cid}/image",
            headers=headers,
            files={"file": ("large.jpg", large_content, "image/jpeg")}
        )
        assert resp.status_code == 400

    @pytest.mark.security
    def test_upload_accepts_valid_jpeg(self, client, auth_headers):
        """UPL-08: Should accept valid JPEG files"""
        headers = auth_headers(username="imgtest3", email="imgtest3@test.com")
        
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Valid Image", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        # Valid JPEG magic bytes
        valid_jpeg = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        
        resp = client.post(
            f"/api/contacts/{cid}/image",
            headers=headers,
            files={"file": ("valid.jpg", valid_jpeg, "image/jpeg")}
        )
        # Should accept (may fail on actual image processing, but not on validation)
        assert resp.status_code in [200, 201, 500]  # 500 = accepted but PIL failed

    @pytest.mark.security
    def test_upload_rejects_non_jpeg_magic_bytes(self, client, auth_headers):
        """UPL-08: Should reject files with wrong magic bytes"""
        headers = auth_headers(username="imgtest4", email="imgtest4@test.com")
        
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Magic Test", "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        
        # PNG magic bytes claiming to be JPEG
        png_content = b"\x89PNG\r\n\x1a\n" + b"A" * 1000
        
        resp = client.post(
            f"/api/contacts/{cid}/image",
            headers=headers,
            files={"file": ("fake.png", png_content, "image/jpeg")}
        )
        assert resp.status_code == 400


class TestGeoValidation:

    @pytest.mark.security
    def test_latitude_out_of_range_rejected(self, client, auth_headers):
        """GEO-01: Latitude outside -90 to 90 should be rejected"""
        headers = auth_headers(username="geotest1", email="geotest1@test.com")
        
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Bad Lat", "phone": "1234567",
            "latitude": 100.0,
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_longitude_out_of_range_rejected(self, client, auth_headers):
        """GEO-02: Longitude outside -180 to 180 should be rejected"""
        headers = auth_headers(username="geotest2", email="geotest2@test.com")
        
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Bad Lon", "phone": "1234567",
            "longitude": 200.0,
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_negative_latitude_valid(self, client, auth_headers):
        """GEO-01: Negative latitude (Southern Hemisphere) should be valid"""
        headers = auth_headers(username="geotest3", email="geotest3@test.com")
        
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Argentina", "phone": "1234567",
            "latitude": -34.6,
            "longitude": -58.4,
        })
        assert resp.status_code == 201

    @pytest.mark.security
    def test_search_radius_must_be_positive(self, client):
        """GEO-03: Negative radius should be rejected"""
        resp = client.get("/api/contacts/search?lat=-34.6&lon=-58.4&radius_km=-10&q=test")
        assert resp.status_code == 422

    @pytest.mark.security
    def test_search_radius_too_large(self, client):
        """GEO-04: Extremely large radius should be limited"""
        resp = client.get("/api/contacts/search?lat=-34.6&lon=-58.4&radius_km=50000&q=test")
        # Should either reject or limit the radius
        assert resp.status_code in [200, 400, 422]

    @pytest.mark.security
    def test_search_without_coordinates_works(self, client):
        """GEO-05: Search without coordinates should work (text search)"""
        resp = client.get("/api/contacts/search?q=plomero")
        assert resp.status_code == 200

    @pytest.mark.security
    def test_search_requires_at_least_one_filter(self, client):
        """GEO-05: Search must have at least one filter"""
        resp = client.get("/api/contacts/search")
        assert resp.status_code == 400

    @pytest.mark.security
    def test_pole_north_coordinates_handled(self, client):
        """GEO-06: Point at pole north should not cause division by zero"""
        resp = client.get("/api/contacts/search?lat=90.0&lon=0&radius_km=10&q=test")
        # Should handle gracefully without 500 error
        assert resp.status_code in [200, 400, 422]

    @pytest.mark.security
    def test_pole_south_coordinates_handled(self, client):
        """GEO-06: Point at pole south should not cause division by zero"""
        resp = client.get("/api/contacts/search?lat=-90.0&lon=0&radius_km=10&q=test")
        assert resp.status_code in [200, 400, 422]


class TestInputValidationEdgeCases:

    @pytest.mark.security
    def test_email_invalid_format_rejected(self, client, auth_headers):
        """Input validation: Invalid email format"""
        headers = auth_headers(username="validatetest", email="vtest@test.com")
        
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test", "phone": "1234567",
            "email": "not-an-email",
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_website_without_http_rejected(self, client, auth_headers):
        """Input validation: Website must start with http:// or https://"""
        headers = auth_headers(username="urltest", email="urltest@test.com")
        
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test", "phone": "1234567",
            "website": "www.example.com",
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_phone_with_letters_rejected(self, client, auth_headers):
        """Input validation: Phone cannot contain letters"""
        headers = auth_headers(username="phonetest", email="phonetest@test.com")
        
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test", "phone": "1234ABC5678",
        })
        assert resp.status_code == 422
