"""Unit tests for service-layer functions and utility helpers.

Expanded coverage:
- escape_like edge cases
- can_edit_field / can_verify_change matrix
- save_history with DB
- resize_image
- get_current_user_optional behavior
- constants validation
"""
import pytest
import jwt
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone
from PIL import Image

from app.routes.contacts import (
    escape_like, resize_image, can_edit_field, can_verify_change, save_history,
    get_current_user_optional, MAX_PENDING_CHANGES, PROTECTED_FIELDS, TRACKED_FIELDS,
)


class TestEscapeLike:

    @pytest.mark.unit
    def test_plain_text_unchanged(self):
        assert escape_like("hello world") == "hello world"

    @pytest.mark.unit
    def test_percent_escaped(self):
        assert escape_like("100%") == "100\\%"

    @pytest.mark.unit
    def test_underscore_escaped(self):
        assert escape_like("foo_bar") == "foo\\_bar"

    @pytest.mark.unit
    def test_backslash_escaped(self):
        assert escape_like("path\\file") == "path\\\\file"

    @pytest.mark.unit
    def test_all_special_chars(self):
        assert escape_like("%_\\") == "\\%\\_\\\\"

    @pytest.mark.unit
    def test_empty_string(self):
        assert escape_like("") == ""

    @pytest.mark.unit
    def test_unicode_unchanged(self):
        assert escape_like("Noño café") == "Noño café"

    @pytest.mark.unit
    def test_mixed_special_and_normal(self):
        assert escape_like("100%_done\\") == "100\\%\\_done\\\\"

    @pytest.mark.unit
    def test_like_wildcard_injection(self):
        """Verify that LIKE wildcards are properly escaped to prevent injection."""
        malicious = "%'; DROP TABLE contacts; --"
        result = escape_like(malicious)
        assert "\\%" in result


class TestCanEditField:

    @pytest.mark.unit
    def test_owner_can_edit_filled(self):
        user = MagicMock(id=1)
        contact = MagicMock(user_id=1)
        can, needs = can_edit_field(user, contact, "name", "Old")
        assert can is True
        assert needs is False

    @pytest.mark.unit
    def test_owner_can_edit_empty(self):
        user = MagicMock(id=1)
        contact = MagicMock(user_id=1)
        can, needs = can_edit_field(user, contact, "description", None)
        assert can is True
        assert needs is False

    @pytest.mark.unit
    def test_moderator_can_edit(self):
        user = MagicMock(id=2, role="moderator")
        contact = MagicMock(user_id=1)
        can, needs = can_edit_field(user, contact, "name", "Old")
        assert can is True
        assert needs is False

    @pytest.mark.unit
    def test_admin_can_edit(self):
        user = MagicMock(id=2, role="admin")
        contact = MagicMock(user_id=1)
        can, needs = can_edit_field(user, contact, "name", "Old")
        assert can is True
        assert needs is False

    @pytest.mark.unit
    def test_registered_user_can_edit_empty_field(self):
        user = MagicMock(id=3, role="user")
        contact = MagicMock(user_id=1)
        can, needs = can_edit_field(user, contact, "description", None)
        assert can is True
        assert needs is True

    @pytest.mark.unit
    def test_registered_user_cannot_edit_filled_field(self):
        user = MagicMock(id=3, role="user")
        contact = MagicMock(user_id=1)
        can, needs = can_edit_field(user, contact, "description", "Existing")
        assert can is False
        assert needs is False

    @pytest.mark.unit
    def test_anonymous_can_edit_empty(self):
        contact = MagicMock(user_id=1)
        can, needs = can_edit_field(None, contact, "description", None)
        assert can is True
        assert needs is True

    @pytest.mark.unit
    def test_anonymous_can_edit_empty_string(self):
        contact = MagicMock(user_id=1)
        can, needs = can_edit_field(None, contact, "description", "")
        assert can is True
        assert needs is True

    @pytest.mark.unit
    def test_anonymous_cannot_edit_filled(self):
        contact = MagicMock(user_id=1)
        can, needs = can_edit_field(None, contact, "description", "Something")
        assert can is False
        assert needs is False

    @pytest.mark.unit
    def test_edge_case_empty_string_is_treated_as_empty(self):
        contact = MagicMock(user_id=1)
        can, _ = can_edit_field(None, contact, "city", "")
        assert can is True

    @pytest.mark.unit
    def test_registered_user_empty_string_treated_as_empty(self):
        user = MagicMock(id=3, role="user")
        contact = MagicMock(user_id=1)
        can, needs = can_edit_field(user, contact, "city", "")
        assert can is True
        assert needs is True


class TestCanVerifyChange:

    @pytest.mark.unit
    def test_owner_can_verify(self):
        user = MagicMock(id=1)
        contact = MagicMock(user_id=1)
        assert can_verify_change(user, contact) is True

    @pytest.mark.unit
    def test_moderator_can_verify(self):
        user = MagicMock(id=2, role="moderator")
        contact = MagicMock(user_id=1)
        assert can_verify_change(user, contact) is True

    @pytest.mark.unit
    def test_admin_can_verify(self):
        user = MagicMock(id=2, role="admin")
        contact = MagicMock(user_id=1)
        assert can_verify_change(user, contact) is True

    @pytest.mark.unit
    def test_regular_user_cannot_verify(self):
        user = MagicMock(id=3, role="user")
        contact = MagicMock(user_id=1)
        assert can_verify_change(user, contact) is False

    @pytest.mark.unit
    def test_none_user_cannot_verify(self):
        contact = MagicMock(user_id=1)
        assert can_verify_change(None, contact) is False


class TestSaveHistory:

    @pytest.fixture
    def history_parent(self, database_session):
        """Create a user and contact so FK constraints pass."""
        from app.models.user import User
        from app.models.contact import Contact
        user = User(
            username="histuser",
            email="hist@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash="hash",
        )
        database_session.add(user)
        database_session.commit()
        contact = Contact(name="Test", phone="1234567", user_id=user.id)
        database_session.add(contact)
        database_session.commit()
        return user.id, contact.id

    @pytest.mark.unit
    def test_saves_when_values_differ(self, database_session, history_parent):
        from app.models.contact import ContactHistory
        user_id, contact_id = history_parent
        save_history(database_session, contact_id=contact_id, user_id=user_id, field_name="name", old_value="Old", new_value="New")
        database_session.flush()
        count = database_session.query(ContactHistory).filter_by(contact_id=contact_id).count()
        assert count == 1

    @pytest.mark.unit
    def test_skips_when_values_equal(self, database_session, history_parent):
        from app.models.contact import ContactHistory
        user_id, contact_id = history_parent
        save_history(database_session, contact_id=contact_id, user_id=user_id, field_name="name", old_value="Same", new_value="Same")
        database_session.flush()
        count = database_session.query(ContactHistory).filter_by(contact_id=contact_id).count()
        assert count == 0

    @pytest.mark.unit
    def test_handles_none_old_value(self, database_session, history_parent):
        from app.models.contact import ContactHistory
        user_id, contact_id = history_parent
        save_history(database_session, contact_id=contact_id, user_id=user_id, field_name="email", old_value=None, new_value="new@test.com")
        database_session.flush()
        record = database_session.query(ContactHistory).filter_by(contact_id=contact_id).first()
        assert record.old_value is None
        assert record.new_value == "new@test.com"

    @pytest.mark.unit
    def test_handles_none_new_value(self, database_session, history_parent):
        from app.models.contact import ContactHistory
        user_id, contact_id = history_parent
        save_history(database_session, contact_id=contact_id, user_id=user_id, field_name="email", old_value="old@test.com", new_value=None)
        database_session.flush()
        record = database_session.query(ContactHistory).filter_by(contact_id=contact_id).first()
        assert record.old_value == "old@test.com"
        assert record.new_value is None

    @pytest.mark.unit
    def test_string_comparison_for_none_vs_empty(self, database_session, history_parent):
        from app.models.contact import ContactHistory
        user_id, contact_id = history_parent
        save_history(database_session, contact_id=contact_id, user_id=user_id, field_name="x", old_value=None, new_value="")
        database_session.flush()
        record = database_session.query(ContactHistory).filter_by(contact_id=contact_id).first()
        assert record is not None
        assert record.new_value == ""

    @pytest.mark.unit
    def test_multiple_history_entries(self, database_session, history_parent):
        from app.models.contact import ContactHistory
        user_id, contact_id = history_parent
        save_history(database_session, contact_id=contact_id, user_id=user_id, field_name="name", old_value="A", new_value="B")
        save_history(database_session, contact_id=contact_id, user_id=user_id, field_name="phone", old_value="111", new_value="222")
        database_session.flush()
        count = database_session.query(ContactHistory).filter_by(contact_id=contact_id).count()
        assert count == 2


class TestResizeImage:

    @pytest.mark.unit
    def test_large_image_resized(self):
        img = Image.new("RGB", (2000, 2000), color="blue")
        resized = resize_image(img, (1024, 1024))
        assert resized.width <= 1024
        assert resized.height <= 1024

    @pytest.mark.unit
    def test_small_image_unchanged(self):
        img = Image.new("RGB", (100, 100), color="red")
        resized = resize_image(img, (1024, 1024))
        assert resized.width == 100
        assert resized.height == 100

    @pytest.mark.unit
    def test_wide_image_maintains_aspect(self):
        img = Image.new("RGB", (2000, 500), color="green")
        resized = resize_image(img, (1024, 1024))
        assert resized.width <= 1024
        assert resized.height <= 1024
        ratio = resized.width / resized.height
        assert 3.5 < ratio < 4.5

    @pytest.mark.unit
    def test_tall_image_maintains_aspect(self):
        img = Image.new("RGB", (500, 2000), color="yellow")
        resized = resize_image(img, (1024, 1024))
        assert resized.width <= 1024
        assert resized.height <= 1024


class TestGetCurrentUserOptional:

    @pytest.mark.unit
    def test_returns_none_when_no_auth_header(self, database_session):
        result = get_current_user_optional(authorization=None, db=database_session)
        assert result is None

    @pytest.mark.unit
    def test_returns_none_when_empty_auth_header(self, database_session):
        result = get_current_user_optional(authorization="", db=database_session)
        assert result is None

    @pytest.mark.unit
    def test_returns_none_when_non_bearer_scheme(self, database_session):
        result = get_current_user_optional(authorization="Basic abc123", db=database_session)
        assert result is None

    @pytest.mark.unit
    def test_returns_none_when_invalid_token(self, database_session):
        result = get_current_user_optional(authorization="Bearer invalid.token.here", db=database_session)
        assert result is None

    @pytest.mark.unit
    def test_returns_none_when_token_missing_sub(self, database_session):
        from app.config import JWT_SECRET, JWT_ALGORITHM
        token = jwt.encode({"exp": datetime.now(timezone.utc) + timedelta(hours=1)}, JWT_SECRET, algorithm=JWT_ALGORITHM)
        result = get_current_user_optional(authorization=f"Bearer {token}", db=database_session)
        assert result is None

    @pytest.mark.unit
    def test_returns_user_when_valid_token(self, database_session):
        from app.config import JWT_SECRET, JWT_ALGORITHM
        from app.models.user import User
        user = User(
            username="optuser",
            email="opt@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash="hash",
            is_active=True,
        )
        database_session.add(user)
        database_session.commit()
        database_session.refresh(user)

        token = jwt.encode({"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, JWT_SECRET, algorithm=JWT_ALGORITHM)
        result = get_current_user_optional(authorization=f"Bearer {token}", db=database_session)
        assert result is not None
        assert result.id == user.id

    @pytest.mark.unit
    def test_returns_none_when_user_inactive(self, database_session):
        from app.config import JWT_SECRET, JWT_ALGORITHM
        from app.models.user import User
        user = User(
            username="inactiveopt",
            email="inactopt@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash="hash",
            is_active=False,
        )
        database_session.add(user)
        database_session.commit()
        database_session.refresh(user)

        token = jwt.encode({"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, JWT_SECRET, algorithm=JWT_ALGORITHM)
        result = get_current_user_optional(authorization=f"Bearer {token}", db=database_session)
        assert result is None


class TestConstants:

    @pytest.mark.unit
    def test_max_pending_changes_is_three(self):
        assert MAX_PENDING_CHANGES == 3

    @pytest.mark.unit
    def test_protected_fields_contains_critical(self):
        critical = ["id", "user_id", "is_verified", "verified_by", "verified_at", "pending_changes_count", "created_at", "updated_at"]
        for field in critical:
            assert field in PROTECTED_FIELDS, f"'{field}' should be in PROTECTED_FIELDS"

    @pytest.mark.unit
    def test_tracked_fields_contains_name(self):
        assert "name" in TRACKED_FIELDS

    @pytest.mark.unit
    def test_tracked_fields_contains_all_expected(self):
        expected = ["name", "phone", "email", "address", "city", "neighborhood",
                    "category_id", "description", "schedule", "website", "photo_path",
                    "latitude", "longitude", "maps_url", "instagram", "facebook", "about"]
        for field in expected:
            assert field in TRACKED_FIELDS, f"'{field}' should be in TRACKED_FIELDS"

    @pytest.mark.unit
    def test_tracked_fields_count(self):
        assert len(TRACKED_FIELDS) == 17
