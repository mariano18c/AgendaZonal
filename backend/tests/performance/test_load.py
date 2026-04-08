"""Performance: Load testing.

Tests for load testing with gradual ramp-up patterns.
"""
import pytest
import time
import concurrent.futures
from tests.conftest import _bearer


class TestLoadTesting:
    """Load testing scenarios."""

    def test_gradual_load_increase(self, client, create_contact):
        """Test system behavior with gradual load increase."""
        contact = create_contact()
        
        # Ramp up from 1 to 10 concurrent requests
        for num_requests in [1, 5, 10]:
            start = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
                futures = [
                    executor.submit(client.get, f"/api/contacts/{contact.id}")
                    for _ in range(num_requests)
                ]
                results = [f.result() for f in futures]
            
            elapsed = time.time() - start
            avg_time = elapsed / num_requests
            
            # All should succeed
            assert all(r.status_code == 200 for r in results)
            # Average time should be reasonable
            assert avg_time < 2.0

    def test_sustained_load(self, client, create_contact):
        """Test sustained load over time."""
        contact = create_contact()
        
        # Make requests over 2 seconds
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < 2:
            r = client.get(f"/api/contacts/{contact.id}")
            assert r.status_code == 200
            request_count += 1
        
        # Should handle at least 10 requests in 2 seconds
        assert request_count >= 10

    def test_concurrent_different_endpoints(self, client, create_contact):
        """Test concurrent requests to different endpoints."""
        contact = create_contact()
        
        def make_requests():
            results = []
            results.append(client.get("/api/categories"))
            results.append(client.get("/api/contacts"))
            results.append(client.get(f"/api/contacts/{contact.id}"))
            return results
        
        # Multiple concurrent users
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_requests) for _ in range(5)]
            all_results = []
            for f in futures:
                all_results.extend(f.result())
        
        # Should handle all requests
        assert all(r.status_code in [200, 201] for r in all_results)


class TestAuthenticationLoad:
    """Load testing for authentication endpoints."""

    def test_login_load(self, client, create_user):
        """Test login endpoint under load."""
        user = create_user()
        
        def login():
            return client.post("/api/auth/login", json={
                "username_or_email": user.username,
                "password": "password123"
            })
        
        # Concurrent logins
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(login) for _ in range(20)]
            results = [f.result() for f in futures]
        
        # Should handle load
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count >= 15  # Allow some rate limiting

    def test_registration_load(self, client):
        """Test registration under load."""
        def register(i):
            return client.post("/api/auth/register", json={
                "username": f"loaduser{i}",
                "email": f"loaduser{i}@test.com",
                "phone_area_code": "0341",
                "phone_number": f"123456{i}",
                "password": "password123"
            })
        
        # Concurrent registrations (should be rate limited)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(register, i) for i in range(10)]
            results = [f.result() for f in futures]
        
        # Should handle with rate limiting
        assert all(r.status_code in [201, 400, 429] for r in results)


class TestSearchLoad:
    """Load testing for search functionality."""

    def test_search_under_load(self, client, create_contact):
        """Test search under concurrent load."""
        # Create some contacts
        for i in range(10):
            create_contact(name=f"Business {i}")
        
        def search():
            return client.get("/api/contacts/search?q=Business")
        
        # Concurrent searches
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(search) for _ in range(20)]
            results = [f.result() for f in futures]
        
        # Should handle load
        assert all(r.status_code == 200 for r in results)

    def test_filtered_search_load(self, client, create_contact):
        """Test filtered search under load."""
        # Create contacts with categories
        for i in range(10):
            create_contact(name=f"Business {i}", category_id=100)
        
        def filtered_search():
            return client.get("/api/contacts?category=100")
        
        # Concurrent filtered searches
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(filtered_search) for _ in range(10)]
            results = [f.result() for f in futures]
        
        assert all(r.status_code == 200 for r in results)


class TestDatabaseLoad:
    """Load testing for database operations."""

    def test_bulk_create_load(self, client, user_headers):
        """Test bulk creation performance."""
        start = time.time()
        
        created = 0
        for i in range(20):
            r = client.post(
                "/api/contacts",
                headers=user_headers,
                json={"name": f"Bulk {i}", "phone": f"123456{i}"}
            )
            if r.status_code == 201:
                created += 1
        
        elapsed = time.time() - start
        
        # Should create efficiently
        assert created >= 15
        assert elapsed < 30  # Should complete in reasonable time

    def test_pagination_load(self, client, create_contact):
        """Test pagination under load."""
        # Create many contacts
        for i in range(50):
            create_contact(name=f"Pagination {i}")
        
        def paginated_request(page):
            return client.get(f"/api/contacts?page={page}&limit=10")
        
        # Request different pages concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(paginated_request, i) for i in range(1, 6)]
            results = [f.result() for f in futures]
        
        assert all(r.status_code == 200 for r in results)


class TestMixedLoad:
    """Mixed load scenarios."""

    def test_mixed_workload(self, client, create_user, create_contact):
        """Test mixed read/write workload."""
        user = create_user()
        contact = create_contact()
        
        def mixed_operations():
            results = []
            # Read operations
            results.append(client.get("/api/categories"))
            results.append(client.get(f"/api/contacts/{contact.id}"))
            results.append(client.get("/api/contacts/search?q=test"))
            
            # Write operations (limited)
            # results.append(client.post(...))
            
            return results
        
        # Concurrent mixed operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(mixed_operations) for _ in range(5)]
            all_results = []
            for f in futures:
                all_results.extend(f.result())
        
        # Should handle mixed workload
        success = sum(1 for r in all_results if r.status_code in [200, 201])
        assert success >= len(all_results) * 0.8

    def test_spike_recovery(self, client, create_contact):
        """Test recovery after load spike."""
        contact = create_contact()
        
        # Normal load
        for _ in range(5):
            r = client.get(f"/api/contacts/{contact.id}")
            assert r.status_code == 200
        
        # Spike
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(client.get, f"/api/contacts/{contact.id}") for _ in range(40)]
            results = [f.result() for f in futures]
        
        spike_success = sum(1 for r in results if r.status_code == 200)
        
        # Recovery
        time.sleep(0.5)
        for _ in range(5):
            r = client.get(f"/api/contacts/{contact.id}")
            assert r.status_code == 200
        
        # Should handle spike and recover
        assert spike_success >= 20  # At least 50% success during spike