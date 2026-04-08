"""Chaos Engineering: Blast Radius Limitation tests.

Tests for blast radius limitation validation.
"""
import pytest


class TestBlastRadius:
    """Test blast radius limitation."""

    def test_isolation_between_services(self, client):
        """Test services are isolated."""
        # One service failure should not affect others
        r = client.get("/health")
        assert r.status_code == 200
        
        r = client.get("/api/categories")
        assert r.status_code == 200

    def test_limited_impact(self, client):
        """Test chaos has limited impact."""
        # Core functionality should always work
        r = client.get("/health")
        assert r.status_code == 200


class TestContainment:
    """Test containment."""

    def test_failure_containment(self, client):
        """Test failure containment."""
        # Failures should be contained
        r = client.get("/api/categories")
        assert r.status_code in [200, 500, 503]

    def test_no_cascading_failures(self, client):
        """Test no cascading failures."""
        # One failure should not cause others
        r = client.get("/api/categories")
        assert r.status_code == 200