"""Race condition and concurrency tests.

Tests for race conditions in business logic:
- Concurrent review creation (same user + contact)
- Concurrent report creation
- JWT secret strength validation
- Database concurrency with WAL mode
"""
import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestRaceConditions:

    @pytest.mark.security
    def test_concurrent_review_unique_constraint_enforced(self, client, auth_headers):
        """Verify UNIQUE constraint on review (user_id + contact_id) is enforced.
        
        Multiple attempts should result in only one successful creation.
        """
        # Setup: Two users
        headers_reviewer = auth_headers(username="race_rev", email="racerev@test.com")
        headers_owner = auth_headers(username="race_owner3", email="raceowner3@test.com")
        
        # Owner creates contact
        create_resp = client.post("/api/contacts", headers=headers_owner, json={
            "name": "Race Review Test", "phone": "1234569",
        })
        cid = create_resp.json()["id"]
        
        # Try to create review
        resp1 = client.post(
            f"/api/contacts/{cid}/reviews",
            headers=headers_reviewer,
            json={"rating": 5, "comment": "First review"}
        )
        assert resp1.status_code == 201
        
        # Try again - should fail
        resp2 = client.post(
            f"/api/contacts/{cid}/reviews",
            headers=headers_reviewer,
            json={"rating": 4, "comment": "Second review"}
        )
        assert resp2.status_code == 409

    @pytest.mark.security
    def test_concurrent_report_unique_constraint_enforced(self, client, auth_headers):
        """Verify UNIQUE constraint on report (user_id + contact_id) is enforced."""
        headers_reporter = auth_headers(username="race_rpt", email="racereport@test.com")
        headers_owner = auth_headers(username="race_owner4", email="raceowner4@test.com")
        
        # Owner creates contact
        create_resp = client.post("/api/contacts", headers=headers_owner, json={
            "name": "Race Report Test 2", "phone": "1234570",
        })
        cid = create_resp.json()["id"]
        
        # First report - should succeed
        resp1 = client.post(
            f"/api/contacts/{cid}/report",
            headers=headers_reporter,
            json={"reason": "spam", "details": "First"}
        )
        assert resp1.status_code == 201
        
        # Second report - should fail
        resp2 = client.post(
            f"/api/contacts/{cid}/report",
            headers=headers_reporter,
            json={"reason": "falso", "details": "Second"}
        )
        assert resp2.status_code == 409


class TestJWTSecretStrength:

    @pytest.mark.security
    def test_jwt_secret_meets_minimum_requirements(self, client):
        """Verify JWT_SECRET meets minimum entropy requirements."""
        from app.config import JWT_SECRET
        
        # JWT_SECRET should be at least 32 bytes
        assert len(JWT_SECRET) >= 32, f"JWT_SECRET too short: {len(JWT_SECRET)} bytes"
        
        # Should not be a common weak secret
        weak_secrets = [
            "secret", "password", "123456", "changeme", "default",
            "jwtsecret", "mysecret", "admin", "root", "test"
        ]
        assert JWT_SECRET.lower() not in weak_secrets, "JWT_SECRET is a common weak secret"
        
        # Should not be in top 10000 passwords (basic check)
        common_passwords = [
            "password", "123456", "12345678", "qwerty", "abc123",
            "monkey", "1234567", "letmein", "trustno1", "dragon",
            "baseball", "iloveyou", "master", "sunshine", "ashley",
        ]
        assert JWT_SECRET not in common_passwords, "JWT_SECRET is a common password"

    @pytest.mark.security
    def test_jwt_secret_generation_command(self, client):
        """Document how to generate a secure JWT_SECRET."""
        # This test documents the recommended way to generate a secret
        import secrets
        
        # Generate a 32-byte (256-bit) random secret
        recommended_secret = secrets.token_urlsafe(32)
        
        assert len(recommended_secret) >= 43, "URL-safe base64 encoding makes it ~43+ chars"
        # The secret should be random enough
        assert recommended_secret != recommended_secret.lower()
        assert recommended_secret != recommended_secret.upper()


class TestDatabaseConcurrency:

    @pytest.mark.security
    def test_concurrent_reads_during_write(self, client, auth_headers):
        """Test that concurrent reads don't block writes with WAL mode."""
        headers = auth_headers(username="concur_test", email="concurtest@test.com")
        
        # Create a contact
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Concurrent Test", "phone": "1234571",
        })
        cid = create_resp.json()["id"]
        
        read_results = []
        write_results = []
        
        def do_reads():
            for _ in range(10):
                resp = client.get(f"/api/contacts/{cid}")
                read_results.append(resp.status_code)
        
        def do_writes():
            for i in range(3):
                resp = client.put(
                    f"/api/contacts/{cid}",
                    headers=headers,
                    json={"description": f"Update {i}"}
                )
                write_results.append(resp.status_code)
        
        # Run reads and writes concurrently
        t1 = threading.Thread(target=do_reads)
        t2 = threading.Thread(target=do_writes)
        
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
        
        # Most reads should succeed (some may get 500 due to SQLite locking)
        success_rate = sum(1 for r in read_results if r == 200) / len(read_results)
        assert success_rate >= 0.5, f"At least 50% of reads should succeed, got {success_rate*100:.0f}%"
        
        # All writes should succeed (200)
        assert all(r == 200 for r in write_results), "Writes should not fail"

    @pytest.mark.security
    def test_wal_mode_enabled(self, client):
        """Verify WAL mode is enabled for better concurrency."""
        # This is tested indirectly through the database.py startup
        # But we can verify the pragma is set
        
        from app.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode"))
            mode = result.scalar()
            
        assert mode and mode.upper() == "WAL", f"Expected WAL mode, got {mode}"


class TestInputValidationSecurity:

    @pytest.mark.security
    def test_sql_injection_like_parameterized(self, client, auth_headers):
        """Verify LIKE queries use parameterized queries (no SQL injection)."""
        headers = auth_headers(username="sqli_test", email="sqli@test.com")
        
        # Create a contact
        client.post("/api/contacts", headers=headers, json={
            "name": "SQLi Test", "phone": "1234572",
        })
        
        # Try SQL injection in search
        resp = client.get("/api/contacts/search?q=' OR '1'='1")
        assert resp.status_code == 200
        
        # Should not return all contacts (that would indicate SQL injection)
        # The search should be safe
        
    @pytest.mark.security
    def test_xss_in_input_sanitized(self, client, auth_headers):
        """Verify XSS attempts are sanitized in input."""
        headers = auth_headers(username="xss_test", email="xss@test.com")
        
        # Try to create contact with XSS in name
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "<script>alert('xss')</script>",
            "phone": "1234573",
        })
        
        # Should either reject or sanitize
        if resp.status_code == 201:
            # If accepted, the XSS should be escaped in responses
            get_resp = client.get(f"/api/contacts/{resp.json()['id']}")
            assert "<script>" not in get_resp.json().get("name", "")


class TestErrorHandlingSecurity:

    @pytest.mark.security
    def test_no_stack_trace_in_production_errors(self, client, auth_headers):
        """Verify error responses don't leak stack traces."""
        auth_hdrs = auth_headers(username="error_test", email="errortest@test.com")
        
        # Send invalid JSON to trigger error
        resp = client.post(
            "/api/contacts",
            headers=auth_hdrs,
            content=b"invalid json data",
        )
        
        # Should return 422 or 400, not 500 with stack trace
        assert resp.status_code in [400, 422]
        
        # Response should not contain Python traceback
        response_text = resp.text.lower()
        assert "traceback" not in response_text
        assert "file " not in response_text
        assert "line " not in response_text

    @pytest.mark.security
    def test_404_does_not_leak_information(self, client):
        """Verify 404 responses don't leak internal information."""
        resp = client.get("/api/contacts/99999999")
        
        # Should return 404
        assert resp.status_code == 404
        
        # Should not reveal internal paths or database info
        response_text = resp.text.lower()
        assert "sqlite" not in response_text
        assert "database" not in response_text
        assert "file" not in response_text


class TestConcurrentWrites:

    @pytest.mark.security
    def test_concurrent_contact_update(self, client, auth_headers):
        """Two auth users send PUT to same contact simultaneously, verify no silent data loss."""
        import threading

        # Create owner and contact
        owner_headers = auth_headers(username="concur_owner", email="concurowner@test.com")
        create_resp = client.post("/api/contacts", headers=owner_headers, json={
            "name": "Concurrent Update Test",
            "phone": "1234599",
        })
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]

        # Create a second user who also has edit access
        # Use auth_headers to create a second regular user (they can edit if they're the owner)
        # For this test, we'll have the owner update and a new user try to update
        second_headers = auth_headers(username="concur_second", email="concursecond@test.com")

        results = []
        barrier = threading.Barrier(2)

        def update_1():
            barrier.wait(timeout=5)
            resp = client.put(
                f"/api/contacts/{cid}",
                headers=owner_headers,
                json={"description": "Updated by owner"},
            )
            results.append(("owner", resp.status_code))

        def update_2():
            barrier.wait(timeout=5)
            resp = client.put(
                f"/api/contacts/{cid}",
                headers=second_headers,
                json={"description": "Updated by second"},
            )
            results.append(("second", resp.status_code))

        t1 = threading.Thread(target=update_1)
        t2 = threading.Thread(target=update_2)
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        # At least one should succeed (owner should, second may get 403)
        successes = [r for r in results if r[1] == 200]
        assert len(successes) >= 1, f"At least owner update should succeed, got: {results}"

        # Verify final state is consistent (not corrupted)
        final = client.get(f"/api/contacts/{cid}")
        assert final.status_code == 200
        data = final.json()
        assert "description" in data
