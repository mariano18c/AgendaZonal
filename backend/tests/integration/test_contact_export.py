"""Integration tests for contact export endpoint."""
import pytest
from app.models.contact import Contact


class TestExportContacts:
    """GET /api/contacts/export"""

    def test_export_csv(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="Test Export", phone="1234567", user_id=user.id, city="Rosario")
        database_session.add(contact)
        database_session.commit()

        resp = client.get("/api/contacts/export?format=csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "Test Export" in resp.text

    def test_export_json(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="JSON Test", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()

        resp = client.get("/api/contacts/export?format=json")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(c["name"] == "JSON Test" for c in data)

    def test_export_invalid_format(self, client):
        resp = client.get("/api/contacts/export?format=xml")
        assert resp.status_code == 422

    def test_export_filtered_by_category(self, client, create_user, database_session):
        from app.models.category import Category
        # Get a real category ID (not code)
        cat = database_session.query(Category).filter(Category.code == 100).first()
        assert cat is not None, "Category 100 should be seeded"

        user = create_user()
        cat1 = Contact(name="Plumber", phone="1111111", user_id=user.id, category_id=cat.id)
        cat2_contact = Contact(name="Barber", phone="2222222", user_id=user.id)
        database_session.add_all([cat1, cat2_contact])
        database_session.commit()

        resp = client.get(f"/api/contacts/export?format=json&category_id={cat.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert all(c["category_id"] == cat.id for c in data)

    def test_export_empty_db(self, client):
        """Export with no contacts should return empty list."""
        resp = client.get("/api/contacts/export?format=json")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_csv_has_header_row(self, client, create_user, database_session):
        user = create_user()
        contact = Contact(name="CSV Test", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()

        resp = client.get("/api/contacts/export?format=csv")
        assert resp.status_code == 200
        lines = resp.text.strip().split('\n')
        header = lines[0]
        assert "name" in header
        assert "phone" in header
