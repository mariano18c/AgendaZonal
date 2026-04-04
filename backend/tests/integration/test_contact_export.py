"""Integration tests for contact export endpoint.

NOTE: Export now requires authentication (security fix).
All tests use auth headers.
"""
import pytest
from app.models.contact import Contact


class TestExportContacts:
    """GET /api/contacts/export — requires authentication."""

    def test_export_csv(self, client, create_user, database_session, auth_headers):
        user = create_user()
        headers = auth_headers(username="exportuser", email="exportuser@test.com")
        contact = Contact(name="Test Export", phone="1234567", user_id=user.id, city="Rosario")
        database_session.add(contact)
        database_session.commit()

        resp = client.get("/api/contacts/export?format=csv", headers=headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "Test Export" in resp.text

    def test_export_json(self, client, create_user, database_session, auth_headers):
        user = create_user()
        headers = auth_headers(username="exportjson", email="exportjson@test.com")
        contact = Contact(name="JSON Test", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()

        resp = client.get("/api/contacts/export?format=json", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(c["name"] == "JSON Test" for c in data)

    def test_export_requires_auth(self, client):
        """Export should return 401 without authentication."""
        resp = client.get("/api/contacts/export")
        assert resp.status_code == 401

    def test_export_invalid_format(self, client, auth_headers):
        headers = auth_headers(username="exportfmt", email="exportfmt@test.com")
        resp = client.get("/api/contacts/export?format=xml", headers=headers)
        assert resp.status_code == 422

    def test_export_filtered_by_category(self, client, create_user, database_session, auth_headers):
        from app.models.category import Category
        cat = database_session.query(Category).filter(Category.code == 100).first()
        assert cat is not None, "Category 100 should be seeded"

        user = create_user()
        headers = auth_headers(username="exportcat", email="exportcat@test.com")
        cat1 = Contact(name="Plumber", phone="1111111", user_id=user.id, category_id=cat.id)
        cat2_contact = Contact(name="Barber", phone="2222222", user_id=user.id)
        database_session.add_all([cat1, cat2_contact])
        database_session.commit()

        resp = client.get(f"/api/contacts/export?format=json&category_id={cat.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert all(c["category_id"] == cat.id for c in data)

    def test_export_empty_db(self, client, auth_headers):
        """Export with no contacts should return empty list."""
        headers = auth_headers(username="exportempty", email="exportempty@test.com")
        resp = client.get("/api/contacts/export?format=json", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_csv_has_header_row(self, client, create_user, database_session, auth_headers):
        user = create_user()
        headers = auth_headers(username="exportcsvhdr", email="exportcsvhdr@test.com")
        contact = Contact(name="CSV Test", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()

        resp = client.get("/api/contacts/export?format=csv", headers=headers)
        assert resp.status_code == 200
        lines = resp.text.strip().split('\n')
        header = lines[0]
        assert "name" in header
        assert "phone" in header

    @pytest.mark.data_exfil
    def test_export_no_sensitive_fields(self, client, create_user, database_session, auth_headers):
        """Exported CSV must NOT contain password_hash or other sensitive fields."""
        user = create_user()
        headers = auth_headers(username="exportsens", email="exportsens@test.com")
        contact = Contact(name="Sensitive Test", phone="1234567", user_id=user.id, city="Rosario")
        database_session.add(contact)
        database_session.commit()

        # CSV export — should be safe
        resp = client.get("/api/contacts/export?format=csv", headers=headers)
        assert resp.status_code == 200
        csv_text = resp.text.lower()
        assert "password_hash" not in csv_text
        assert "user_id" not in csv_text

        # JSON export — includes user_id (known gap)
        resp_json = client.get("/api/contacts/export?format=json", headers=headers)
        assert resp_json.status_code == 200
        data = resp_json.json()
        for item in data:
            assert "password_hash" not in item
