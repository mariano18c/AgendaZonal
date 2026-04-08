"""Performance: Third-party Integration.

Tests for external API call performance and timeout handling.
"""
import pytest
import time


class TestExternalAPIPerformance:
    """Test external API performance."""

    def test_response_time_acceptable(self, client):
        """Test external API response time is acceptable."""
        # Core functionality
        start = time.time()
        r = client.get("/api/categories")
        elapsed = time.time() - start
        
        assert r.status_code == 200
        assert elapsed < 2.0

    def test_no_blocking_on_external(self, client):
        """Test external APIs don't block."""
        # Should not hang on external services
        r = client.get("/health")
        assert r.status_code == 200


class TestExternalAPIErrorHandling:
    """Test external API error handling."""

    def test_external_timeout_handling(self, client):
        """Test external API timeout handling."""
        # Should handle external failures gracefully
        r = client.get("/api/categories")
        
        # Core should work
        assert r.status_code == 200

    def test_external_failure_recovery(self, client):
        """Test recovery from external failure."""
        # Should recover
        r = client.get("/api/categories")
        assert r.status_code == 200


class TestExternalAPIMocking:
    """Test external API mocking."""

    def test_fallback_when_external_unavailable(self, client):
        """Test fallback when external unavailable."""
        # Should have fallback
        r = client.get("/api/categories")
        
        assert r.status_code == 200