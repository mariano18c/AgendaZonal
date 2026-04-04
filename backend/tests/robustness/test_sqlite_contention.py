"""Robustness tests for SQLite lock contention handling."""
import pytest
import threading


class TestSQLiteContention:
    """Test concurrent writes under lock contention."""

    @pytest.mark.robustness
    def test_concurrent_writes_graceful_handling(self, client, auth_headers):
        """Multiple simultaneous write requests should not expose stack traces."""
        headers = auth_headers(username="sqlite_test", email="sqlitetest@test.com")

        # Create a contact
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Contention Test",
            "phone": "3419999999",
        })
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]

        errors = []
        results = []

        def do_update(i):
            resp = client.put(
                f"/api/contacts/{cid}",
                headers=headers,
                json={"description": f"Update {i}"},
            )
            results.append(resp.status_code)
            # Check no stack trace exposure
            if resp.status_code >= 500:
                text = resp.text.lower()
                if "traceback" in text or "file " in text:
                    errors.append(f"Stack trace exposed in update {i}")

        threads = []
        for i in range(5):
            t = threading.Thread(target=do_update, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=15)

        # No stack traces should be exposed
        assert len(errors) == 0, f"Stack traces exposed: {errors}"

        # Most requests should get a valid response (200 or rate-limited 429)
        valid = [s for s in results if s in [200, 429, 409]]
        assert len(valid) >= len(results) * 0.6, \
            f"At least 60% should get valid responses, got {len(valid)}/{len(results)}: {results}"

    @pytest.mark.robustness
    def test_no_internal_error_on_contention(self, client, auth_headers):
        """SQLite lock errors should not expose internal details."""
        headers = auth_headers(username="sqlite_test2", email="sqlitetest2@test.com")

        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Error Test",
            "phone": "3418888888",
        })
        cid = create_resp.json()["id"]

        # Rapid concurrent writes
        results = []

        def rapid_update():
            for _ in range(3):
                resp = client.put(
                    f"/api/contacts/{cid}",
                    headers=headers,
                    json={"description": "Rapid update"},
                )
                results.append(resp)

        t1 = threading.Thread(target=rapid_update)
        t2 = threading.Thread(target=rapid_update)
        t1.start()
        t2.start()
        t1.join(timeout=15)
        t2.join(timeout=15)

        # Check no internal error details leaked
        for resp in results:
            if resp.status_code >= 500:
                text = resp.text.lower()
                assert "sqlite" not in text, "SQLite details exposed"
                assert "operationalerror" not in text, "SQLAlchemy error exposed"
                assert "traceback" not in text, "Traceback exposed"
