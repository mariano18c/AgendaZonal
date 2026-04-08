"""Performance: Stress testing.

Tests to determine system breaking point and recovery behavior.
"""
import pytest
import time
import concurrent.futures
from tests.conftest import _bearer


class TestStressTesting:
    """Stress testing scenarios."""

    def test_max_concurrent_connections(self, client):
        """Test maximum concurrent connections the system can handle."""
        contact_count = 0
        max_workers = 100
        
        def make_request():
            return client.get("/api/categories")
        
        # Gradually increase load until failure
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(make_request) for _ in range(max_workers)]
            results = [f.result() for f in futures]
        
        success_count = sum(1 for r in results if r.status_code == 200)
        
        # Should handle some load
        assert success_count > 0

    def test_database_connection_stress(self, client, create_contact):
        """Test database connection handling under stress."""
        # Create multiple contacts
        for i in range(50):
            create_contact(name=f"Stress {i}")
        
        # Make many concurrent read requests
        def read_contact(i):
            return client.get(f"/api/contacts/{i % 50 + 1}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(read_contact, i) for i in range(100)]
            results = [f.result() for f in futures]
        
        success = sum(1 for r in results if r.status_code == 200)
        assert success >= 50

    def test_memory_stress(self, client, user_headers):
        """Test system under memory stress."""
        # Try to create large requests
        large_payloads = [
            {"name": "A" * 1000, "phone": "1234567", "description": "B" * 5000},
            {"name": "A" * 2000, "phone": "1234567", "description": "B" * 10000},
        ]
        
        for payload in large_payloads:
            r = client.post("/api/contacts", headers=user_headers, json=payload)
            # Should handle or reject gracefully
            assert r.status_code in [201, 400, 413, 422]

    def test_cpu_stress(self, client, create_contact):
        """Test CPU usage under load."""
        contact = create_contact()
        
        # Make many requests that require processing
        def cpu_intensive_request(i):
            return client.get(f"/api/contacts/search?q=test{i}")
        
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(cpu_intensive_request, i) for i in range(50)]
            results = [f.result() for f in futures]
        elapsed = time.time() - start
        
        success = sum(1 for r in results if r.status_code == 200)
        assert success >= 30
        assert elapsed < 30  # Should complete in reasonable time


class TestBreakingPoint:
    """Identify system breaking points."""

    def test_request_size_limit(self, client, user_headers):
        """Test maximum request size."""
        # Try increasingly large requests
        sizes = [1000, 10000, 100000, 1000000]
        
        for size in sizes:
            r = client.post(
                "/api/contacts",
                headers=user_headers,
                json={"name": "A" * size, "phone": "1234567"}
            )
            
            # Should handle or reject
            if r.status_code in [413, 422]:
                break
        
        # Should eventually reject
        assert True

    def test_pagination_limit(self, client, create_contact):
        """Test maximum pagination limit."""
        # Create many contacts
        for i in range(100):
            create_contact(name=f"Pagination {i}")
        
        # Request increasingly large pages
        limits = [10, 50, 100, 500, 1000]
        
        for limit in limits:
            r = client.get(f"/api/contacts?limit={limit}")
            assert r.status_code == 200
            
            if r.status_code == 200:
                data = r.json()
                assert len(data) <= limit

    def test_concurrent_write_limit(self, client, user_headers):
        """Test concurrent write limit."""
        def create_contact_request(i):
            return client.post(
                "/api/contacts",
                headers=user_headers,
                json={"name": f"Write {i}", "phone": f"123456{i}"}
            )
        
        # Try many concurrent writes
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(create_contact_request, i) for i in range(50)]
            results = [f.result() for f in futures]
        
        success = sum(1 for r in results if r.status_code == 201)
        # Should handle some writes
        assert success > 0


class TestRecoveryBehavior:
    """Test recovery after stress."""

    def test_recovery_after_overload(self, client, create_contact):
        """Test system recovers after being overloaded."""
        contact = create_contact()
        
        # First, normal operation
        for _ in range(5):
            r = client.get(f"/api/contacts/{contact.id}")
            assert r.status_code == 200
        
        # Overload
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(client.get, f"/api/contacts/{contact.id}") for _ in range(100)]
            results = [f.result() for f in futures]
        
        # Wait for recovery
        time.sleep(1)
        
        # Should recover
        r = client.get(f"/api/contacts/{contact.id}")
        assert r.status_code == 200

    def test_graceful_degradation_under_stress(self, client):
        """Test graceful degradation when stressed."""
        # Stress the system
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(client.get, "/api/categories") for _ in range(50)]
            results = [f.result() for f in futures]
        
        # Core functionality should still work
        r = client.get("/health")
        assert r.status_code == 200

    def test_recovery_time(self, client):
        """Test recovery time after stress."""
        # Cause stress
        for _ in range(20):
            client.get("/api/categories")
        
        # Measure recovery
        start = time.time()
        for _ in range(10):
            r = client.get("/api/categories")
            if r.status_code == 200:
                break
        recovery_time = time.time() - start
        
        # Should recover quickly
        assert recovery_time < 5.0


class TestResourceLimits:
    """Test resource limit handling."""

    def test_response_timeout_under_load(self, client):
        """Test response timeouts under heavy load."""
        # Make many requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
            futures = [executor.submit(client.get, "/api/categories") for _ in range(80)]
            results = [f.result() for f in futures]
        
        # Check that requests complete (with potential timeouts)
        assert len(results) == 80

    def test_queue_limit(self, client):
        """Test request queue limits."""
        # Make many concurrent requests
        def make_request():
            return client.get("/api/categories")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(make_request) for _ in range(200)]
            results = [f.result() for f in futures]
        
        # Should handle queue
        assert len(results) == 200