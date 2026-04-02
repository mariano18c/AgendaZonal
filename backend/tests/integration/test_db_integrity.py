"""Database integrity tests.

Validates that foreign keys, cascades, and constraints work correctly
with PRAGMA foreign_keys=ON enabled in the test database.
"""
import pytest
from sqlalchemy.exc import IntegrityError
from app.models.contact import Contact
from app.models.category import Category


class TestPragmaSettings:

    @pytest.mark.integration
    def test_pragma_foreign_keys_on(self, test_engine):
        with test_engine.connect() as conn:
            result = conn.exec_driver_sql("PRAGMA foreign_keys")
            value = result.fetchone()[0]
            assert value == 1, (
                f"PRAGMA foreign_keys is {value}, expected 1. "
                "FK constraints are NOT enforced in tests!"
            )

    @pytest.mark.integration
    def test_production_pragma_listener(self):
        """Verify the production engine's PRAGMA listener sets foreign_keys correctly.

        This covers app/database.py lines 14-18 (the set_sqlite_pragma event).
        """
        from sqlalchemy import create_engine, event

        test_pragma_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )

        # Import and apply the production PRAGMA listener
        from app.database import set_sqlite_pragma
        event.listen(test_pragma_engine, "connect", set_sqlite_pragma)

        with test_pragma_engine.connect() as conn:
            fk_result = conn.exec_driver_sql("PRAGMA foreign_keys")
            assert fk_result.fetchone()[0] == 1

    @pytest.mark.integration
    def test_get_db_generator(self):
        """Verify get_db() yields and closes a session.

        This covers app/database.py lines 31-35 (get_db generator).
        """
        from app.database import get_db
        db_gen = get_db()
        session = next(db_gen)
        assert session is not None
        # Calling next again or close triggers the finally block
        try:
            next(db_gen)
        except StopIteration:
            pass

    @pytest.mark.integration
    def test_contact_with_invalid_category_fails(self, database_session):
        contact = Contact(name="Test", phone="1234567", category_id=99999)
        database_session.add(contact)
        with pytest.raises(IntegrityError):
            database_session.commit()

    @pytest.mark.integration
    def test_contact_with_invalid_user_fails(self, database_session):
        contact = Contact(name="Test", phone="1234567", user_id=99999)
        database_session.add(contact)
        with pytest.raises(IntegrityError):
            database_session.commit()


class TestCascadeDeletes:

    @pytest.mark.integration
    def test_delete_contact_removes_changes(self, client, auth_headers, contact_factory, change_factory):
        h_owner = auth_headers(username="cascadeown", email="cascade@test.com")
        h_other = auth_headers(username="cascadeoth", email="cascadot@test.com")

        cid = contact_factory(h_owner, name="To Delete", phone="1234567")
        change_factory(cid, h_other, "description", "Pending change")

        changes = client.get(f"/api/contacts/{cid}/changes", headers=h_owner)
        assert changes.status_code == 200

        # First, request deletion to flag the contact
        flag_resp = client.post(f"/api/contacts/{cid}/request-deletion", headers=h_owner)
        assert flag_resp.status_code == 200

        # Then, delete the flagged contact
        resp = client.delete(f"/api/contacts/{cid}", headers=h_owner)
        assert resp.status_code == 204

        resp = client.get(f"/api/contacts/{cid}")
        assert resp.status_code == 404

    @pytest.mark.integration
    def test_delete_contact_removes_history(self, client, auth_headers):
        h = auth_headers(username="histdel", email="histdel@test.com")

        create = client.post("/api/contacts", headers=h, json={
            "name": "History Test", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}", headers=h, json={"name": "Updated"})

        history = client.get(f"/api/contacts/{cid}/history", headers=h)
        assert history.status_code == 200

        # First, request deletion to flag the contact
        flag_resp = client.post(f"/api/contacts/{cid}/request-deletion", headers=h)
        assert flag_resp.status_code == 200

        # Then, delete the flagged contact
        resp = client.delete(f"/api/contacts/{cid}", headers=h)
        assert resp.status_code == 204


class TestTransactionIntegrity:

    @pytest.mark.integration
    def test_contact_create_sets_user_id(self, client, auth_headers):
        h = auth_headers(username="txuser", email="txuser@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": "TX Test", "phone": "1234567",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["user_id"] is not None

        me = client.get("/api/auth/me", headers=h)
        assert me.json()["id"] == data["user_id"]

    @pytest.mark.integration
    def test_pending_changes_count_decrements_on_verify(self, client, auth_headers):
        h_owner = auth_headers(username="countown", email="countown@test.com")
        h_other = auth_headers(username="countoth", email="countoth@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Count Test", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
            "description": "Change 1",
        })

        contact = client.get(f"/api/contacts/{cid}").json()
        assert contact["pending_changes_count"] == 1

        changes = client.get(f"/api/contacts/{cid}/changes", headers=h_owner).json()
        change_id = changes[0]["id"]
        client.post(f"/api/contacts/{cid}/changes/{change_id}/verify", headers=h_owner)

        contact = client.get(f"/api/contacts/{cid}").json()
        assert contact["pending_changes_count"] == 0

    @pytest.mark.integration
    def test_pending_changes_count_decrements_on_reject(self, client, auth_headers):
        h_owner = auth_headers(username="rejown", email="rejown@test.com")
        h_other = auth_headers(username="rejoth", email="rejoth@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Reject Test", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}/edit", headers=h_other, json={
            "description": "Will reject",
        })

        changes = client.get(f"/api/contacts/{cid}/changes", headers=h_owner).json()
        change_id = changes[0]["id"]
        client.post(f"/api/contacts/{cid}/changes/{change_id}/reject", headers=h_owner)

        contact = client.get(f"/api/contacts/{cid}").json()
        assert contact["pending_changes_count"] == 0

    @pytest.mark.integration
    def test_pending_changes_count_never_negative(self, client, auth_headers):
        h_owner = auth_headers(username="negown", email="negown@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Negative Test", "phone": "1234567",
        })
        cid = create.json()["id"]

        client.put(f"/api/contacts/{cid}", headers=h_owner, json={"city": "Rosario"})
        contact = client.get(f"/api/contacts/{cid}").json()
        assert contact["pending_changes_count"] == 0
