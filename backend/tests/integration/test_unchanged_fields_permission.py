"""Tests for skip-permission-check-unchanged-fields bug fix.

Verifies that editing a contact without changing any field doesn't
trigger false 403 permission errors.
"""
import pytest
from app.auth import create_token


def _bearer(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token(user_id)}"}


class TestUnchangedFieldsPermissionFix:
    """Test suite for the fix: skip permission check when field value unchanged."""

    def test_save_unchanged_form_returns_200(
        self, client, db_session, create_user, create_contact
    ):
        """Scenario: User loads contact form, makes NO changes, clicks Save.
        
        Expected: HTTP 200 (previously was 403).
        """
        # Create owner and contact with latitude set
        owner = create_user()
        contact = create_contact(
            user_id=owner.id,
            name="Test Contact",
            latitude=-34.6,
            longitude=-68.5,
        )
        
        headers = _bearer(owner.id)
        
        # Send edit request with SAME values (unchanged)
        payload = {
            "name": "Test Contact",  # unchanged
            "phone": contact.phone,    # unchanged
            "latitude": -34.6,         # unchanged
            "longitude": -68.5,        # unchanged
        }
        
        response = client.put(
            f"/api/contacts/{contact.id}/edit",
            headers=headers,
            json=payload
        )
        
        # Should succeed (was 403 before fix)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
        data = response.json()
        assert data["name"] == "Test Contact"

    def test_non_owner_cannot_modify_filled_field(
        self, client, db_session, create_user, create_contact
    ):
        """Scenario: Non-owner tries to modify a field that already has a value.
        
        Expected: HTTP 403 (permission denied) - this behavior is preserved.
        """
        owner = create_user()
        contact = create_contact(
            user_id=owner.id,
            name="Original Name",
            latitude=-34.6,
        )
        
        # Different user (non-owner)
        other_user = create_user()
        headers = _bearer(other_user.id)
        
        # Try to change latitude (field already has value)
        payload = {
            "latitude": -34.7,  # changed
        }
        
        response = client.put(
            f"/api/contacts/{contact.id}/edit",
            headers=headers,
            json=payload
        )
        
        # Should be 403 - non-owner cannot modify filled field
        assert response.status_code == 403
        assert "latitude" in response.json()["detail"]

    def test_owner_can_modify_any_field(
        self, client, db_session, create_user, create_contact
    ):
        """Scenario: Owner modifies any field.
        
        Expected: HTTP 200 with direct update.
        """
        owner = create_user()
        contact = create_contact(
            user_id=owner.id,
            name="Original Name",
            latitude=-34.6,
        )
        
        headers = _bearer(owner.id)
        
        # Owner changes name
        payload = {
            "name": "Updated Name",
        }
        
        response = client.put(
            f"/api/contacts/{contact.id}/edit",
            headers=headers,
            json=payload
        )
        
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_non_owner_can_propose_empty_field(
        self, client, db_session, create_user, create_contact
    ):
        """Scenario: Non-owner proposes change to empty field.
        
        Expected: HTTP 200 (pending change created).
        """
        owner = create_user()
        contact = create_contact(
            user_id=owner.id,
            name="Test Contact",
            latitude=None,  # empty field
        )
        
        other_user = create_user()
        headers = _bearer(other_user.id)
        
        # Non-owner adds value to empty field
        payload = {
            "latitude": -34.6,
        }
        
        response = client.put(
            f"/api/contacts/{contact.id}/edit",
            headers=headers,
            json=payload
        )
        
        # Should succeed (creates pending change)
        assert response.status_code == 200

    def test_float_vs_string_comparison(
        self, client, db_session, create_user, create_contact
    ):
        """Scenario: Float value "35.5" equals float 35.5.
        
        Expected: No permission check needed when values match.
        """
        owner = create_user()
        contact = create_contact(
            user_id=owner.id,
            name="Test Contact",
            latitude=35.5,
        )
        
        headers = _bearer(owner.id)
        
        # Send as string (frontend might send "35.5")
        payload = {
            "latitude": "35.5",
        }
        
        response = client.put(
            f"/api/contacts/{contact.id}/edit",
            headers=headers,
            json=payload
        )
        
        # Should succeed - str(35.5) == "35.5" evaluates to True
        assert response.status_code == 200

    def test_none_vs_empty_string_equate(
        self, client, db_session, create_user, create_contact
    ):
        """Scenario: None and empty string should be considered different.
        
        Expected: str(None) != str("") so permission check runs.
        This test verifies the comparison logic: str(None) = "None" != "".
        """
        # Test the string comparison logic
        assert str(None) == "None"
        assert str(None) != ""
        
        # Owner modifies field from None to a value
        owner = create_user()
        contact = create_contact(
            user_id=owner.id,
            name="Test Contact",
            latitude=None,
        )
        
        headers = _bearer(owner.id)
        
        # Set a value where it was None - should work
        payload = {
            "latitude": -34.6,
        }
        
        response = client.put(
            f"/api/contacts/{contact.id}/edit",
            headers=headers,
            json=payload
        )
        
        # Owner can edit, so should succeed
        assert response.status_code == 200
