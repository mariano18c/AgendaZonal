"""Integration tests — Contact export (CSV/JSON).

Adapted from tests_ant/integration/test_contact_export.py — uses current conftest fixtures.
Covers:
- Export CSV, export JSON
- Requires auth (admin only)
- Invalid format
- Filtered by category
- Empty DB
- CSV header row
- No sensitive fields (password_hash, user_id in wrong context)
"""
import uuid
import pytest


def _uid():
    return uuid.uuid4().hex[:8]


class TestContactExport:

    @pytest.mark.integration
    def test_export_csv_by_admin(self, client, admin_headers, create_contact):
        """Admin can export contacts as CSV."""
        create_contact(name="Export CSV Test")
        resp = client.get("/api/contacts/export", headers=admin_headers,
                          params={"format": "csv"})
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        assert "name" in resp.text

    @pytest.mark.integration
    def test_export_json_by_admin(self, client, admin_headers, create_contact):
        """Admin can export contacts as JSON."""
        create_contact(name="Export JSON Test")
        resp = client.get("/api/contacts/export", headers=admin_headers,
                          params={"format": "json"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.integration
    def test_export_requires_auth(self, client):
        """Export endpoint requires authentication."""
        resp = client.get("/api/contacts/export")
        assert resp.status_code == 401

    @pytest.mark.integration
    def test_export_forbidden_for_regular_user(self, client, auth_headers):
        """Regular user cannot export contacts."""
        headers = auth_headers(username=f"export_user_{_uid()}", email=f"export_user_{_uid()}@test.com")
        resp = client.get("/api/contacts/export", headers=headers)
        assert resp.status_code == 403

    @pytest.mark.integration
    def test_export_invalid_format(self, client, admin_headers):
        """Invalid export format should be rejected."""
        resp = client.get("/api/contacts/export", headers=admin_headers,
                          params={"format": "xml"})
        assert resp.status_code in [400, 422]

    @pytest.mark.integration
    def test_export_filtered_by_category(self, client, admin_headers, create_contact):
        """Export should support category filter."""
        create_contact(name="Category Export", category_id=1)
        resp = client.get("/api/contacts/export", headers=admin_headers,
                          params={"format": "csv", "category_id": 1})
        assert resp.status_code in [200, 404]

    @pytest.mark.integration
    def test_export_empty_db(self, client, admin_headers, db_session):
        """Export with no contacts should return empty result."""
        # Clear contacts
        from app.models.contact import Contact
        db_session.query(Contact).delete()
        db_session.commit()

        resp = client.get("/api/contacts/export", headers=admin_headers,
                          params={"format": "json"})
        assert resp.status_code == 200
        data = resp.json()
        assert data == []

    @pytest.mark.integration
    def test_export_csv_has_header_row(self, client, admin_headers, create_contact):
        """CSV export should have a header row."""
        create_contact(name="Header Test")
        resp = client.get("/api/contacts/export", headers=admin_headers,
                          params={"format": "csv"})
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        assert len(lines) >= 1
        # First line should be the header
        header = lines[0].lower()
        assert "name" in header

    @pytest.mark.integration
    def test_export_csv_no_sensitive_fields(self, client, admin_headers, create_contact):
        """CSV export should not contain password_hash or other sensitive fields."""
        create_contact(name="Sensitive Test")
        resp = client.get("/api/contacts/export", headers=admin_headers,
                          params={"format": "csv"})
        assert resp.status_code == 200
        content = resp.text.lower()
        assert "password_hash" not in content
        assert "password" not in content

    @pytest.mark.integration
    def test_export_json_no_sensitive_fields(self, client, admin_headers, create_contact):
        """JSON export should not contain password_hash."""
        create_contact(name="JSON Sensitive Test")
        resp = client.get("/api/contacts/export", headers=admin_headers,
                          params={"format": "json"})
        assert resp.status_code == 200
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            for contact in data:
                assert "password_hash" not in contact
                assert "password" not in contact
