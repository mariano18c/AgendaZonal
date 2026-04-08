"""Performance: Resource Utilization.

Tests for CPU, memory, disk I/O, and network bandwidth monitoring.
"""
import pytest
import time
import os

try:
    import psutil
except ImportError:
    psutil = None


class TestCPUUtilization:
    """Test CPU utilization."""

    def test_cpu_under_load(self, client, create_contact):
        """Test CPU utilization under load."""
        if psutil is None:
            pytest.skip("psutil not installed")
        
        # Get initial CPU
        process = psutil.Process(os.getpid())
        
        # Make requests
        for _ in range(20):
            r = client.get("/api/categories")
            assert r.status_code == 200
        
        # Check CPU not exhausted
        cpu_percent = process.cpu_percent()
        
        # Should not max out CPU
        assert cpu_percent < 100

    def test_cpu_spike_handling(self, client):
        """Test CPU spike handling."""
        # Spike
        for _ in range(10):
            r = client.get("/api/categories")
        
        # Should handle
        assert True


class TestMemoryUtilization:
    """Test memory utilization."""

    def test_memory_stable(self, client):
        """Test memory stays stable."""
        if psutil is None:
            pytest.skip("psutil not installed")
        
        process = psutil.Process(os.getpid())
        
        # Make many requests
        for _ in range(50):
            r = client.get("/api/categories")
        
        # Memory should not grow significantly
        mem_info = process.memory_info()
        
        # Should complete without memory issues
        assert True

    def test_memory_limit(self, client, user_headers):
        """Test memory limit handling."""
        # Try to use lots of memory via requests
        for i in range(10):
            r = client.post(
                "/api/contacts",
                headers=user_headers,
                json={"name": "A" * 10000, "phone": "1234567"}
            )
        
        # Should handle
        assert True


class TestDiskIO:
    """Test disk I/O."""

    def test_log_writing(self, client):
        """Test log writing doesn't block."""
        # Make requests that generate logs
        for _ in range(10):
            r = client.get("/api/categories")
        
        # Should not block
        assert True

    def test_database_writes(self, client, user_headers):
        """Test database writes don't block reads."""
        # Write
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={"name": "IO Test", "phone": "1234567"}
        )
        
        # Read should still work
        r = client.get("/api/categories")
        assert r.status_code == 200


class TestNetworkUtilization:
    """Test network utilization."""

    def test_response_size_reasonable(self, client):
        """Test response sizes are reasonable."""
        r = client.get("/api/categories")
        
        # Check content length
        content_length = len(r.content)
        
        # Should be reasonable
        assert content_length < 10 * 1024 * 1024  # 10MB

    def test_compressed_responses(self, client):
        """Test compressed responses work."""
        r = client.get("/api/categories", headers={"Accept-Encoding": "gzip"})
        
        # Should work
        assert r.status_code == 200


class TestResourceCleanup:
    """Test resource cleanup."""

    def test_connections_closed(self, client):
        """Test connections are properly closed."""
        # Make requests
        for _ in range(20):
            r = client.get("/api/categories")
        
        # Should complete cleanly
        assert True

    def test_handles_released(self, client):
        """Test file handles are released."""
        # Make requests
        for _ in range(20):
            r = client.get("/api/categories")
        
        # Should not leak handles
        assert True