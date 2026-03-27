"""Unit tests for service-layer functions and utility helpers."""
import pytest
from pydantic import ValidationError
from unittest.mock import MagicMock

from app.routes.contacts import escape_like, resize_image, can_edit_field, can_verify_change, save_history
from app.schemas.contact import ContactCreate, ContactUpdate, ContactChangeCreate
from app.schemas.user import UserCreate, UserUpdate, UserRoleUpdate, PasswordReset
from app.schemas.auth import RegisterRequest
from PIL import Image


# ---------------------------------------------------------------------------
# escape_like
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# can_edit_field
# ---------------------------------------------------------------------------
class TestCanEditField:

    @pytest.mark.unit
    def test_owner_can_edit_filled(self):
        user = MagicMock()
        user.id = 1
        contact = MagicMock()
        contact.user_id = 1
        can, needs = can_edit_field(user, contact, "name", "Old")
        assert can is True
        assert needs is False

    @pytest.mark.unit
    def test_owner_can_edit_empty(self):
        user = MagicMock()
        user.id = 1
        contact = MagicMock()
        contact.user_id = 1
        can, needs = can_edit_field(user, contact, "description", None)
        assert can is True
        assert needs is False

    @pytest.mark.unit
    def test_moderator_can_edit(self):
        user = MagicMock()
        user.id = 2
        user.role = "moderator"
        contact = MagicMock()
        contact.user_id = 1
        can, needs = can_edit_field(user, contact, "name", "Old")
        assert can is True
        assert needs is False

    @pytest.mark.unit
    def test_admin_can_edit(self):
        user = MagicMock()
        user.id = 2
        user.role = "admin"
        contact = MagicMock()
        contact.user_id = 1
        can, needs = can_edit_field(user, contact, "name", "Old")
        assert can is True
        assert needs is False

    @pytest.mark.unit
    def test_registered_user_can_edit_empty_field(self):
        user = MagicMock()
        user.id = 3
        user.role = "user"
        contact = MagicMock()
        contact.user_id = 1
        can, needs = can_edit_field(user, contact, "description", None)
        assert can is True
        assert needs is True

    @pytest.mark.unit
    def test_registered_user_cannot_edit_filled_field(self):
        user = MagicMock()
        user.id = 3
        user.role = "user"
        contact = MagicMock()
        contact.user_id = 1
        can, needs = can_edit_field(user, contact, "description", "Existing")
        assert can is False
        assert needs is False

    @pytest.mark.unit
    def test_anonymous_can_edit_empty(self):
        contact = MagicMock()
        contact.user_id = 1
        can, needs = can_edit_field(None, contact, "description", None)
        assert can is True
        assert needs is True

    @pytest.mark.unit
    def test_anonymous_can_edit_empty_string(self):
        contact = MagicMock()
        contact.user_id = 1
        can, needs = can_edit_field(None, contact, "description", "")
        assert can is True
        assert needs is True

    @pytest.mark.unit
    def test_anonymous_cannot_edit_filled(self):
        contact = MagicMock()
        contact.user_id = 1
        can, needs = can_edit_field(None, contact, "description", "Something")
        assert can is False
        assert needs is False


# ---------------------------------------------------------------------------
# can_verify_change
# ---------------------------------------------------------------------------
class TestCanVerifyChange:

    @pytest.mark.unit
    def test_owner_can_verify(self):
        user = MagicMock()
        user.id = 1
        contact = MagicMock()
        contact.user_id = 1
        assert can_verify_change(user, contact) is True

    @pytest.mark.unit
    def test_moderator_can_verify(self):
        user = MagicMock()
        user.id = 2
        user.role = "moderator"
        contact = MagicMock()
        contact.user_id = 1
        assert can_verify_change(user, contact) is True

    @pytest.mark.unit
    def test_admin_can_verify(self):
        user = MagicMock()
        user.id = 2
        user.role = "admin"
        contact = MagicMock()
        contact.user_id = 1
        assert can_verify_change(user, contact) is True

    @pytest.mark.unit
    def test_regular_user_cannot_verify(self):
        user = MagicMock()
        user.id = 3
        user.role = "user"
        contact = MagicMock()
        contact.user_id = 1
        assert can_verify_change(user, contact) is False

    @pytest.mark.unit
    def test_none_user_cannot_verify(self):
        contact = MagicMock()
        contact.user_id = 1
        assert can_verify_change(None, contact) is False


# ---------------------------------------------------------------------------
# save_history
# ---------------------------------------------------------------------------
class TestSaveHistory:

    @pytest.mark.unit
    def test_saves_when_values_differ(self, db_session):
        from app.models.contact import ContactHistory
        save_history(db_session, contact_id=1, user_id=1, field_name="name", old_value="Old", new_value="New")
        db_session.flush()
        count = db_session.query(ContactHistory).filter_by(contact_id=1).count()
        assert count == 1

    @pytest.mark.unit
    def test_skips_when_values_equal(self, db_session):
        from app.models.contact import ContactHistory
        save_history(db_session, contact_id=1, user_id=1, field_name="name", old_value="Same", new_value="Same")
        db_session.flush()
        count = db_session.query(ContactHistory).filter_by(contact_id=1).count()
        assert count == 0

    @pytest.mark.unit
    def test_handles_none_old_value(self, db_session):
        from app.models.contact import ContactHistory
        save_history(db_session, contact_id=1, user_id=1, field_name="email", old_value=None, new_value="new@test.com")
        db_session.flush()
        record = db_session.query(ContactHistory).filter_by(contact_id=1).first()
        assert record.old_value is None
        assert record.new_value == "new@test.com"

    @pytest.mark.unit
    def test_handles_none_new_value(self, db_session):
        from app.models.contact import ContactHistory
        save_history(db_session, contact_id=1, user_id=1, field_name="email", old_value="old@test.com", new_value=None)
        db_session.flush()
        record = db_session.query(ContactHistory).filter_by(contact_id=1).first()
        assert record.old_value == "old@test.com"
        assert record.new_value is None


# ---------------------------------------------------------------------------
# resize_image
# ---------------------------------------------------------------------------
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
        # Aspect ratio should be maintained
        ratio = resized.width / resized.height
        assert 3.5 < ratio < 4.5


# ---------------------------------------------------------------------------
# UserCreate / UserUpdate schemas
# ---------------------------------------------------------------------------
class TestUserCreateSchema:

    @pytest.mark.unit
    def test_valid_user_create(self):
        u = UserCreate(
            username="newuser",
            email="new@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password="password123",
            role="user",
        )
        assert u.username == "newuser"
        assert u.role == "user"

    @pytest.mark.unit
    def test_invalid_role_accepted_by_schema(self):
        """UserCreate schema accepts any string for role (validation is in the route)."""
        u = UserCreate(
            username="newuser",
            email="new@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password="password123",
            role="superadmin",
        )
        assert u.role == "superadmin"

    @pytest.mark.unit
    def test_password_too_short(self):
        with pytest.raises(ValidationError):
            UserCreate(
                username="newuser",
                email="new@test.com",
                phone_area_code="0341",
                phone_number="1234567",
                password="short",
                role="user",
            )

    @pytest.mark.unit
    def test_username_too_short(self):
        with pytest.raises(ValidationError):
            UserCreate(
                username="ab",
                email="new@test.com",
                phone_area_code="0341",
                phone_number="1234567",
                password="password123",
                role="user",
            )


class TestUserUpdateSchema:

    @pytest.mark.unit
    def test_partial_update(self):
        u = UserUpdate(email="new@test.com")
        assert u.email == "new@test.com"
        assert u.username is None

    @pytest.mark.unit
    def test_empty_update(self):
        u = UserUpdate()
        assert u.username is None
        assert u.role is None


class TestUserRoleUpdateSchema:

    @pytest.mark.unit
    def test_valid_role_update(self):
        r = UserRoleUpdate(role="moderator")
        assert r.role == "moderator"


class TestPasswordResetSchema:

    @pytest.mark.unit
    def test_valid_password_reset(self):
        p = PasswordReset(new_password="newpassword123")
        assert p.new_password == "newpassword123"

    @pytest.mark.unit
    def test_short_password_rejected(self):
        with pytest.raises(ValidationError):
            PasswordReset(new_password="short")
