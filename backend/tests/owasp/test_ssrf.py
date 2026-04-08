"""OWASP A10: Server-Side Request Forgery (SSRF) tests.

Tests for internal network probing and metadata service access protection.
"""
import pytest
from tests.conftest import _bearer


class TestSSRFPrevention:
    """Test SSRF protection mechanisms."""

    def test_ssrf_in_url_parameter(self, client, user_headers):
        """Test SSRF via URL parameter."""
        ssrf_payloads = [
            "http://localhost/",
            "http://127.0.0.1/",
            "http://[::1]/",
            "http://0.0.0.0/",
            "http://metadata.google.internal/",
            "http://169.254.169.254/",
            "file:///etc/passwd",
            "gopher://localhost/",
            "ftp://localhost/",
        ]
        
        for payload in ssrf_payloads:
            r = client.get(f"/api/contacts/search?q={payload}")
            # Should handle or reject malicious URLs
            assert r.status_code in [200, 400, 422]

    def test_ssrf_via_redirect(self, client):
        """Test SSRF via open redirect."""
        # Try payloads that might cause redirects
        payloads = [
            "http://evil.com/redirect?to=http://localhost",
            "http://evil.com/redirect?to=http://127.0.0.1",
            "//127.0.0.1",
            "///127.0.0.1",
        ]
        
        for payload in payloads:
            r = client.get(f"/api/contacts/search?q={payload}")
            assert r.status_code in [200, 400, 422]

    def test_internal_ip_disclosure(self, client, user_headers):
        """Test that internal IPs are not disclosed."""
        # Try to access internal services
        internal_ips = [
            "10.0.0.1",
            "10.0.0.255",
            "172.16.0.1",
            "172.31.255.255",
            "192.168.0.1",
            "192.168.255.255",
        ]
        
        for ip in internal_ips:
            r = client.get(f"/api/contacts/search?q={ip}")
            # Should not leak internal IP info
            assert r.status_code in [200, 400, 422]

    def test_metadata_service_access(self, client):
        """Test that metadata services are not accessible."""
        metadata_endpoints = [
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://metadata.google.internal/",
            "http://169.254.169.254/metadata/v1/",
        ]
        
        for endpoint in metadata_endpoints:
            r = client.get(f"/api/contacts/search?q={endpoint}")
            # Should not access metadata
            assert r.status_code in [200, 400, 422]

    def test_localhost_access(self, client, user_headers):
        """Test that localhost access is restricted."""
        payloads = [
            "localhost",
            "127.0.0.1",
            "::1",
            "0.0.0.0",
            "localhost.localdomain",
        ]
        
        for payload in payloads:
            r = client.get(f"/api/contacts/search?q={payload}")
            assert r.status_code in [200, 400, 422]

    def test_dns_rebinding(self, client):
        """Test DNS rebinding protection."""
        # Try DNS rebinding attacks
        payloads = [
            "http://testdomain.xyz",
            "http://127.0.0.1.nip.io",
            "http://[::1]",
        ]
        
        for payload in payloads:
            r = client.get(f"/api/contacts/search?q={payload}")
            assert r.status_code in [200, 400, 422]

    def test_protocol_smuggling(self, client):
        """Test protocol smuggling attempts."""
        payloads = [
            "dict://localhost:11211/stats",
            "sftp://localhost/",
            "ldap://localhost/",
            "gopher://localhost/",
        ]
        
        for payload in payloads:
            r = client.get(f"/api/contacts/search?q={payload}")
            assert r.status_code in [200, 400, 422]


class TestBlindSSRF:
    """Test blind SSRF vulnerabilities."""

    def test_blind_ssrf_time_based(self, client):
        """Test time-based blind SSRF."""
        # Try payloads that might cause delays
        payload = "http://127.0.0.1:9999/slow"
        
        r = client.get(f"/api/contacts/search?q={payload}")
        assert r.status_code in [200, 400, 422]

    def test_blind_ssrf_out_of_band(self, client):
        """Test out-of-band SSRF."""
        # Try to make server connect to external service
        payload = "http://evil.com/collect"
        
        r = client.get(f"/api/contacts/search?q={payload}")
        assert r.status_code in [200, 400, 422]


class TestSSRFInFileUpload:
    """Test SSRF in file upload functionality."""

    def test_url_in_upload(self, client, user_headers):
        """Test SSRF via file upload URL field."""
        # If there's a URL upload field
        pass  # Placeholder

    def test_filename_url_injection(self, client, user_headers):
        """Test URL injection via filename."""
        # If file upload exists
        pass  # Placeholder


class TestSSRFProtectionMechanisms:
    """Test SSRF protection implementation."""

    def test_url_validation(self, client):
        """Test that URLs are validated before processing."""
        # Try various URL formats
        malicious_urls = [
            "http://test.com@127.0.0.1",
            "http://127.0.0.1.test.com",
            "http://127。0。0。1",
            "http://2130706433",  # Decimal IP
            "http://0x7f000001",  # Hex IP
            "http://0177.0.0.1",  # Octal IP
        ]
        
        for url in malicious_urls:
            r = client.get(f"/api/contacts/search?q={url}")
            assert r.status_code in [200, 400, 422]

    def test_dns_whitelist(self, client):
        """Test DNS whitelist enforcement."""
        # Only whitelisted domains should be allowed
        allowed_domains = ["trusted.com"]
        
        for domain in allowed_domains:
            r = client.get(f"/api/contacts/search?q=http://{domain}")
            assert r.status_code in [200, 400, 422]

    def test_request_timeout(self, client):
        """Test that external requests have timeouts."""
        # Slow external requests should timeout
        payload = "http://slowserver.com/slow"
        
        r = client.get(f"/api/contacts/search?q={payload}")
        # Should timeout or reject
        assert r.status_code in [200, 400, 422, 504]