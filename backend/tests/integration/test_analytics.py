"""Integration tests for analytics and CSV export."""
import pytest


class TestAnalytics:
    """Analytics with zone filter and CSV export."""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_headers, contact_factory, moderator_user):
        self.owner_headers = auth_headers(username="anl_owner", email="anlowner@test.com")
        self.mod_user, self.mod_headers = moderator_user
        self.contact_id = contact_factory(
            self.owner_headers, name="Analytics Contact", phone="3411111111",
            category_id=1, city="Rosario",
        )

    def test_analytics_returns_data(self, client):
        resp = client.get("/api/admin/analytics", headers=self.mod_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_providers" in data
        assert "active_providers" in data
        assert "total_leads" in data
        assert "avg_rating" in data
        assert "top_categories" in data

    def test_analytics_with_zone_filter(self, client):
        """Zone filter should return metrics for matching contacts only."""
        resp = client.get("/api/admin/analytics", headers=self.mod_headers, params={"zone": "Rosario"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["zone"] == "Rosario"
        assert "total_providers" in data

    def test_analytics_non_mod_rejected(self, client):
        resp = client.get("/api/admin/analytics", headers=self.owner_headers)
        assert resp.status_code == 403

    def test_csv_export_valid(self, client):
        """CSV export should have correct Content-Type and headers."""
        resp = client.get("/api/admin/analytics/export", headers=self.mod_headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "nombre" in resp.text  # CSV header

    def test_csv_export_unauthenticated(self, client):
        resp = client.get("/api/admin/analytics/export")
        # May return 401 or 403 depending on auth setup
        assert resp.status_code in [401, 403]
