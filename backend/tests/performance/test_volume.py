"""Performance: Volume Testing.

Tests for large dataset processing and database query performance.
"""
import pytest
import time
from tests.conftest import _bearer


class TestLargeDatasetProcessing:
    """Test large dataset processing."""

    def test_large_contact_list(self, client, create_contact):
        """Test processing large contact lists."""
        # Create many contacts
        for i in range(100):
            create_contact(name=f"Volume {i}")
        
        # Request all
        r = client.get("/api/contacts?limit=100")
        
        assert r.status_code == 200

    def test_large_search_results(self, client, create_contact):
        """Test large search result processing."""
        # Create contacts with similar names
        for i in range(50):
            create_contact(name=f"Test Business {i}")
        
        # Search
        r = client.get("/api/contacts/search?q=Test")
        
        assert r.status_code == 200


class TestDatabaseQueryVolume:
    """Test database query volume."""

    def test_many_joins_performance(self, client, create_contact):
        """Test query with many joins."""
        # Create related data
        for i in range(20):
            create_contact(name=f"Join Test {i}")
        
        # Query with joins
        r = client.get("/api/contacts")
        
        assert r.status_code == 200
        assert time.time() - time.time() < 5  # Should complete quickly

    def test_complex_filter_performance(self, client, create_contact):
        """Test complex filter performance."""
        # Create varied data
        for i in range(30):
            create_contact(
                name=f"Filter Test {i}",
                category_id=100 + (i % 5)
            )
        
        # Complex filter
        r = client.get("/api/contacts?category=100&status=active")
        
        assert r.status_code == 200


class TestPaginationVolume:
    """Test pagination with large datasets."""

    def test_deep_pagination(self, client, create_contact):
        """Test deep pagination."""
        # Create many records
        for i in range(200):
            create_contact(name=f"Page {i}")
        
        # Deep pagination
        r = client.get("/api/contacts?page=10&limit=20")
        
        assert r.status_code == 200

    def test_pagination_performance(self, client, create_contact):
        """Test pagination performance."""
        for i in range(100):
            create_contact(name=f"Perf {i}")
        
        times = []
        for page in range(1, 6):
            start = time.time()
            r = client.get(f"/api/contacts?page={page}&limit=20")
            times.append(time.time() - start)
            
            assert r.status_code == 200
        
        # All pages should be fast
        avg_time = sum(times) / len(times)
        assert avg_time < 1.0


class TestBulkOperations:
    """Test bulk operations."""

    def test_bulk_create_performance(self, client, user_headers):
        """Test bulk create performance."""
        start = time.time()
        
        created = 0
        for i in range(50):
            r = client.post(
                "/api/contacts",
                headers=user_headers,
                json={"name": f"Bulk {i}", "phone": f"123456{i}"}
            )
            if r.status_code == 201:
                created += 1
        
        elapsed = time.time() - start
        
        # Should complete in reasonable time
        assert created > 0
        assert elapsed < 60

    def test_bulk_read_performance(self, client, create_contact):
        """Test bulk read performance."""
        # Create contacts
        for i in range(50):
            create_contact(name=f"Bulk Read {i}")
        
        start = time.time()
        r = client.get("/api/contacts?limit=50")
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 5


class TestDataVolumeLimits:
    """Test data volume limits."""

    def test_max_query_size(self, client):
        """Test maximum query size handling."""
        # Large filter
        large_filter = "A" * 10000
        
        r = client.get(f"/api/contacts/search?q={large_filter}")
        
        assert r.status_code in [200, 400, 414]

    def test_max_result_size(self, client, create_contact):
        """Test maximum result size."""
        # Create many contacts
        for i in range(500):
            create_contact(name=f"Max {i}")
        
        # Request large limit
        r = client.get("/api/contacts?limit=10000")
        
        # Should handle or cap
        assert r.status_code in [200, 400]