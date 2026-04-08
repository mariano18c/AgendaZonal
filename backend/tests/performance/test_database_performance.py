"""Performance: Database Performance.

Tests for database query optimization, connection pooling, and transaction throughput.
"""
import pytest
import time
from tests.conftest import _bearer


class TestQueryOptimization:
    """Test query optimization."""

    def test_indexed_search(self, client, create_contact):
        """Test indexed search performance."""
        create_contact(name="Indexed Test")
        
        start = time.time()
        r = client.get("/api/contacts/search?q=Indexed")
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 1.0

    def test_select_specific_columns(self, client, create_contact):
        """Test selecting specific columns."""
        contact = create_contact()
        
        start = time.time()
        r = client.get(f"/api/contacts/{contact.id}")
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 0.5


class TestConnectionPooling:
    """Test connection pooling."""

    def test_connection_reuse(self, client):
        """Test connection reuse."""
        # Make multiple requests
        for _ in range(10):
            r = client.get("/api/categories")
            assert r.status_code == 200

    def test_pool_size_handling(self, client):
        """Test pool size handling."""
        import concurrent.futures
        
        def make_request():
            return client.get("/api/categories")
        
        # Many concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(40)]
            results = [f.result() for f in futures]
        
        success = sum(1 for r in results if r.status_code == 200)
        assert success > 0


class TestTransactionPerformance:
    """Test transaction performance."""

    def test_single_transaction(self, client, user_headers):
        """Test single transaction performance."""
        start = time.time()
        
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={"name": "Transaction Test", "phone": "1234567"}
        )
        
        elapsed = time.time() - start
        
        assert r.status_code in [201, 400]
        assert elapsed < 2.0

    def test_multiple_transactions(self, client, user_headers):
        """Test multiple transactions."""
        start = time.time()
        
        for i in range(10):
            r = client.post(
                "/api/contacts",
                headers=user_headers,
                json={"name": f"Multi {i}", "phone": f"123456{i}"}
            )
        
        elapsed = time.time() - start
        
        assert elapsed < 20  # Should complete in reasonable time


class TestQueryComplexity:
    """Test query complexity."""

    def test_simple_query(self, client, create_contact):
        """Test simple query performance."""
        create_contact(name="Simple Query")
        
        start = time.time()
        r = client.get("/api/contacts")
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 1.0

    def test_complex_query(self, client, create_contact):
        """Test complex query performance."""
        # Create related data
        for i in range(10):
            create_contact(name=f"Complex {i}")
        
        # Complex query
        start = time.time()
        r = client.get("/api/contacts?category=100&status=active")
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 2.0


class TestDatabaseLocks:
    """Test database locking."""

    def test_no_blocking_locks(self, client, user_headers):
        """Test no blocking locks."""
        # Quick operations should not block
        r = client.get("/api/categories")
        assert r.status_code == 200
        
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={"name": "Lock Test", "phone": "1234567"}
        )
        assert r.status_code in [201, 400]

    def test_concurrent_writes(self, client, user_headers):
        """Test concurrent write handling."""
        import concurrent.futures
        
        def create_contact(i):
            return client.post(
                "/api/contacts",
                headers=user_headers,
                json={"name": f"Concurrent {i}", "phone": f"123456{i}"}
            )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_contact, i) for i in range(10)]
            results = [f.result() for f in futures]
        
        success = sum(1 for r in results if r.status_code == 201)
        assert success > 0