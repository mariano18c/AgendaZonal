"""Integration tests — Pending changes (create, verify, reject, delete)."""
import pytest
from tests.conftest import _bearer


class TestEditWithPendingChanges:
    """Test the edit endpoint that creates pending changes for non-owners."""

    def test_owner_edits_directly(self, client, create_user, create_contact):
        user = create_user()
        c = create_contact(user_id=user.id, description="Original")
        r = client.put(f"/api/contacts/{c.id}/edit", headers=_bearer(user), json={
            "description": "Updated by owner",
        })
        assert r.status_code == 200
        assert r.json()["description"] == "Updated by owner"

    def test_stranger_creates_pending_change(self, client, create_user, create_contact):
        c = create_contact(description="")  # empty = editable by anyone
        stranger = create_user()
        r = client.put(f"/api/contacts/{c.id}/edit", headers=_bearer(stranger), json={
            "description": "Suggestion from stranger",
        })
        assert r.status_code == 200
        # Check pending count increased
        r2 = client.get(f"/api/contacts/{c.id}")
        assert r2.json()["pending_changes_count"] >= 1

    def test_anon_fills_empty_field(self, client, create_contact):
        c = create_contact(description="")
        r = client.put(f"/api/contacts/{c.id}/edit", json={
            "description": "Anon suggestion",
        })
        assert r.status_code == 200

    def test_anon_cannot_edit_filled_field(self, client, create_contact):
        c = create_contact(description="Already filled")
        r = client.put(f"/api/contacts/{c.id}/edit", json={
            "description": "Trying to overwrite",
        })
        assert r.status_code == 403

    def test_max_pending_changes(self, client, create_user, create_contact, db_session):
        c = create_contact(description="")
        c.pending_changes_count = 3  # Already at max
        db_session.commit()
        stranger = create_user()
        r = client.put(f"/api/contacts/{c.id}/edit", headers=_bearer(stranger), json={
            "description": "One more",
        })
        assert r.status_code == 400
        assert "máximo" in r.json()["detail"].lower()


class TestChangesLifecycle:
    def test_get_changes(self, client, create_user, create_contact, db_session):
        from app.models.contact_change import ContactChange
        user = create_user()
        c = create_contact(user_id=user.id)
        change = ContactChange(
            contact_id=c.id, user_id=user.id,
            field_name="name", old_value="Old", new_value="New",
            is_verified=False,
        )
        db_session.add(change)
        c.pending_changes_count = 1
        db_session.commit()
        r = client.get(f"/api/contacts/{c.id}/changes", headers=_bearer(user))
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_changes_forbidden(self, client, create_user, create_contact):
        c = create_contact()
        stranger = create_user()
        r = client.get(f"/api/contacts/{c.id}/changes", headers=_bearer(stranger))
        assert r.status_code == 403

    def test_verify_change(self, client, create_user, create_contact, db_session):
        from app.models.contact_change import ContactChange
        user = create_user()
        c = create_contact(user_id=user.id, name="Original")
        change = ContactChange(
            contact_id=c.id, user_id=create_user().id,
            field_name="name", old_value="Original", new_value="Updated",
            is_verified=False,
        )
        db_session.add(change)
        c.pending_changes_count = 1
        db_session.commit()
        db_session.refresh(change)

        r = client.post(f"/api/contacts/{c.id}/changes/{change.id}/verify",
                          headers=_bearer(user))
        assert r.status_code == 200
        assert r.json()["is_verified"] is True

        # Check contact was updated
        r2 = client.get(f"/api/contacts/{c.id}")
        assert r2.json()["name"] == "Updated"

    def test_reject_change(self, client, create_user, create_contact, db_session):
        from app.models.contact_change import ContactChange
        user = create_user()
        c = create_contact(user_id=user.id)
        change = ContactChange(
            contact_id=c.id, user_id=create_user().id,
            field_name="description", old_value="", new_value="Suggestion",
            is_verified=False,
        )
        db_session.add(change)
        c.pending_changes_count = 1
        db_session.commit()
        db_session.refresh(change)

        r = client.post(f"/api/contacts/{c.id}/changes/{change.id}/reject",
                          headers=_bearer(user))
        assert r.status_code == 200

    def test_delete_own_change(self, client, create_user, create_contact, db_session):
        from app.models.contact_change import ContactChange
        suggester = create_user()
        c = create_contact()
        change = ContactChange(
            contact_id=c.id, user_id=suggester.id,
            field_name="description", old_value="", new_value="My suggestion",
            is_verified=False,
        )
        db_session.add(change)
        c.pending_changes_count = 1
        db_session.commit()
        db_session.refresh(change)

        r = client.delete(f"/api/contacts/{c.id}/changes/{change.id}",
                           headers=_bearer(suggester))
        assert r.status_code == 200

    def test_delete_others_change_forbidden(self, client, create_user, create_contact, db_session):
        from app.models.contact_change import ContactChange
        suggester = create_user()
        other = create_user()
        c = create_contact()
        change = ContactChange(
            contact_id=c.id, user_id=suggester.id,
            field_name="description", old_value="", new_value="X",
            is_verified=False,
        )
        db_session.add(change)
        c.pending_changes_count = 1
        db_session.commit()
        db_session.refresh(change)

        r = client.delete(f"/api/contacts/{c.id}/changes/{change.id}",
                           headers=_bearer(other))
        assert r.status_code == 403
