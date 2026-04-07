"""Integration tests for phone search endpoint. Merged from tests_ant."""
from app.models.contact import Contact


class TestSearchByPhone:
    """GET /api/contacts/search/phone"""

    def test_search_finds_partial_match(self, client, create_user, db_session):
        user = create_user()
        contact = Contact(name="Test", phone="03411234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        resp = client.get("/api/contacts/search/phone?phone=1234567")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_minimum_phone_length(self, client):
        resp = client.get("/api/contacts/search/phone?phone=ab")
        assert resp.status_code == 422

    def test_no_results_returns_empty(self, client):
        resp = client.get("/api/contacts/search/phone?phone=9999999999")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_suspended_contacts_not_shown(self, client, create_user, db_session):
        user = create_user()
        contact = Contact(name="Suspended", phone="03411111111", user_id=user.id, status="suspended")
        db_session.add(contact)
        db_session.commit()
        resp = client.get("/api/contacts/search/phone?phone=1111111")
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_active_and_suspended_filter(self, client, create_user, db_session):
        user = create_user()
        active = Contact(name="Active", phone="1111111", user_id=user.id, status="active")
        suspended = Contact(name="Suspended", phone="1111112", user_id=user.id, status="suspended")
        db_session.add_all([active, suspended])
        db_session.commit()
        resp = client.get("/api/contacts/search/phone?phone=11111")
        assert resp.status_code == 200
        names = [c["name"] for c in resp.json()]
        assert "Active" in names
        assert "Suspended" not in names
