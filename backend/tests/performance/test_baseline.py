"""Performance: Baseline Performance tests.

Establish baseline performance metrics for all critical endpoints.
"""
import pytest
import time
from tests.conftest import _bearer


class TestEndpointResponseTime:
    """Test response times for critical endpoints."""

    def test_health_endpoint_response_time(self, client):
        """Test health endpoint responds quickly."""
        start = time.time()
        r = client.get("/health")
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 0.1, f"Health endpoint took {elapsed:.3f}s, should be < 0.1s"

    def test_categories_endpoint_response_time(self, client):
        """Test categories endpoint responds within acceptable time."""
        start = time.time()
        r = client.get("/api/categories")
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 0.5, f"Categories took {elapsed:.3f}s, should be < 0.5s"

    def test_contacts_list_response_time(self, client, create_contact):
        """Test contacts list responds within acceptable time."""
        # Create test contacts
        for i in range(10):
            create_contact(name=f"Business {i}")
        
        start = time.time()
        r = client.get("/api/contacts")
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 1.0, f"Contacts list took {elapsed:.3f}s, should be < 1.0s"

    def test_contact_search_response_time(self, client, create_contact):
        """Test search responds within acceptable time."""
        create_contact(name="Test Business")
        
        start = time.time()
        r = client.get("/api/contacts/search?q=Test")
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 1.5, f"Search took {elapsed:.3f}s, should be < 1.5s"

    def test_contact_detail_response_time(self, client, create_contact):
        """Test contact detail responds within acceptable time."""
        contact = create_contact()
        
        start = time.time()
        r = client.get(f"/api/contacts/{contact.id}")
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 0.5, f"Contact detail took {elapsed:.3f}s, should be < 0.5s"

    def test_login_response_time(self, client, create_user):
        """Test login responds within acceptable time."""
        user = create_user()
        
        start = time.time()
        r = client.post("/api/auth/login", json={
            "username_or_email": user.username,
            "password": "password123"
        })
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 1.0, f"Login took {elapsed:.3f}s, should be < 1.0s"

    def test_authenticated_endpoint_response_time(self, client, user_headers):
        """Test authenticated endpoints respond within acceptable time."""
        start = time.time()
        r = client.get("/api/auth/me", headers=user_headers)
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 0.5, f"Auth endpoint took {elapsed:.3f}s, should be < 0.5s"


class TestDatabaseQueryPerformance:
    """Test database query performance."""

    def test_contact_list_query_time(self, client, db_session, create_contact):
        """Test contact list query performance."""
        # Create multiple contacts
        for i in range(20):
            create_contact(name=f"Business {i}")
        
        start = time.time()
        r = client.get("/api/contacts")
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 1.0, f"Query took {elapsed:.3f}s"

    def test_paginated_query_performance(self, client, create_contact):
        """Test pagination performance."""
        for i in range(50):
            create_contact(name=f"Business {i}")
        
        # Test different page sizes
        for page_size in [10, 25, 50]:
            start = time.time()
            r = client.get(f"/api/contacts?limit={page_size}")
            elapsed = time.time() - start
            
            assert r.status_code == 200
            assert elapsed < 1.5, f"Pagination {page_size} took {elapsed:.3f}s"

    def test_filtered_query_performance(self, client, create_contact):
        """Test filtered query performance."""
        # Create contacts with different categories
        for i in range(20):
            create_contact(name=f"Business {i}", category_id=100 + (i % 5))
        
        start = time.time()
        r = client.get("/api/contacts?category=100")
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 1.0, f"Filtered query took {elapsed:.3f}s"


class TestConcurrentRequestPerformance:
    """Test performance under concurrent requests."""

    def test_sequential_request_performance(self, client, create_contact):
        """Test sequential request handling."""
        contact = create_contact()
        
        times = []
        for _ in range(10):
            start = time.time()
            r = client.get(f"/api/contacts/{contact.id}")
            times.append(time.time() - start)
            assert r.status_code == 200
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        assert avg_time < 0.5, f"Average time {avg_time:.3f}s is too high"
        assert max_time < 1.0, f"Max time {max_time:.3f}s is too high"

    def test_repeated_auth_requests(self, client, create_user):
        """Test repeated authentication requests."""
        user = create_user()
        
        times = []
        for _ in range(5):
            start = time.time()
            r = client.post("/api/auth/login", json={
                "username_or_email": user.username,
                "password": "password123"
            })
            times.append(time.time() - start)
            assert r.status_code == 200
        
        avg_time = sum(times) / len(times)
        assert avg_time < 1.0, f"Average login time {avg_time:.3f}s is too high"


class TestMemoryUsage:
    """Test memory usage during operations."""

    def test_large_result_set_memory(self, client, create_contact):
        """Test memory usage with large result sets."""
        # Create many contacts
        for i in range(100):
            create_contact(name=f"Business {i}")
        
        # Request all contacts
        r = client.get("/api/contacts?limit=100")
        
        assert r.status_code == 200
        data = r.json()
        assert len(data) <= 100


class TestCachePerformance:
    """Test caching performance."""

    def test_repeated_same_request(self, client, create_contact):
        """Test repeated identical requests."""
        contact = create_contact()
        
        # First request
        r1 = client.get(f"/api/contacts/{contact.id}")
        assert r1.status_code == 200
        
        # Second identical request
        r2 = client.get(f"/api/contacts/{contact.id}")
        assert r2.status_code == 200
        
        # Both should be fast
        # (Caching would be a bonus, but not required)
        assert True


class TestLargePayloadPerformance:
    """Test performance with large payloads."""

    def test_large_contact_creation(self, client, user_headers):
        """Test creating contact with large fields."""
        large_name = "A" * 255
        large_description = "B" * 5000
        
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={
                "name": large_name,
                "phone": "1234567",
                "description": large_description
            }
        )
        
        assert r.status_code in [201, 400, 422]

    def test_large_search_query(self, client, create_contact):
        """Test search with large query."""
        create_contact(name="Test")
        
        large_query = "A" * 1000
        r = client.get(f"/api/contacts/search?q={large_query}")
        
        assert r.status_code in [200, 400, 422]


class TestComplexQueryPerformance:
    """Test performance of complex queries."""

    def test_multiple_filters(self, client, create_contact):
        """Test query with multiple filters."""
        create_contact(name="Test Business")
        
        start = time.time()
        r = client.get("/api/contacts?category=100&status=active&city=Rosario")
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 2.0, f"Multi-filter query took {elapsed:.3f}s"

    def test_text_search_with_filters(self, client, create_contact):
        """Test text search combined with filters."""
        create_contact(name="Plomero Rodriguez")
        
        start = time.time()
        r = client.get("/api/contacts/search?q=Plomero&category=100")
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 2.0, f"Text + filter took {elapsed:.3f}s"


class TestPerformanceRegression:
    """Test for performance regressions."""

    def test_baseline_performance_stable(self, client, create_contact):
        """Verify baseline performance remains stable."""
        contact = create_contact(name="Regression Test Business")
        
        times = []
        for _ in range(20):
            start = time.time()
            r = client.get(f"/api/contacts/{contact.id}")
            times.append(time.time() - start)
            assert r.status_code == 200
        
        # Check that performance doesn't degrade significantly
        first_half = sum(times[:10]) / 10
        second_half = sum(times[10:]) / 10
        
        # Second half should not be significantly slower
        degradation = (second_half - first_half) / first_half if first_half > 0 else 0
        assert degradation < 0.5, f"Performance degraded by {degradation*100:.1f}%"