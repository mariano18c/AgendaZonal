"""Unit tests for SQLAlchemy model constraints.

Adapted from tests_ant/unit/test_models.py — uses current conftest fixtures.
Validates that model definitions enforce:
- Foreign key relationships
- Unique constraints
- Nullable constraints
- Default values
- Column types and lengths
"""
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.category import Category
from app.models.contact import Contact, ContactHistory
from app.models.contact_change import ContactChange


def _uid():
    """Generate a short unique string to avoid UNIQUE constraint collisions."""
    return uuid.uuid4().hex[:8]


class TestUserModel:

    @pytest.mark.unit
    def test_user_unique_username(self, db_session):
        user1 = User(
            username=f"unique_{_uid()}",
            email=f"a_{_uid()}@test.com",
            phone_area_code="0341",
            phone_number="1111111",
            password_hash="hash1",
        )
        db_session.add(user1)
        db_session.commit()

        user2 = User(
            username=user1.username,
            email=f"b_{_uid()}@test.com",
            phone_area_code="0341",
            phone_number="2222222",
            password_hash="hash2",
        )
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    @pytest.mark.unit
    def test_user_unique_email(self, db_session):
        user1 = User(
            username=f"user_a_{_uid()}",
            email=f"same_{_uid()}@test.com",
            phone_area_code="0341",
            phone_number="1111111",
            password_hash="hash1",
        )
        db_session.add(user1)
        db_session.commit()

        user2 = User(
            username=f"user_b_{_uid()}",
            email=user1.email,
            phone_area_code="0341",
            phone_number="2222222",
            password_hash="hash2",
        )
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    @pytest.mark.unit
    def test_user_default_role_is_user(self, db_session):
        user = User(
            username=f"default_{_uid()}",
            email=f"default_{_uid()}@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash="hash",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        assert user.role == "user"

    @pytest.mark.unit
    def test_user_default_is_active_true(self, db_session):
        user = User(
            username=f"active_{_uid()}",
            email=f"active_{_uid()}@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash="hash",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        assert user.is_active is True

    @pytest.mark.unit
    def test_user_nullable_fields(self, db_session):
        """phone_area_code and phone_number are NOT nullable — should raise."""
        user = User(
            username=f"no_phone_{_uid()}",
            email=f"nophone_{_uid()}@test.com",
            password_hash="hash",
        )
        db_session.add(user)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestCategoryModel:

    @pytest.mark.unit
    def test_category_unique_code(self, db_session):
        cat = Category(code=888, name="TestCat", icon="test", description="Test")
        db_session.add(cat)
        db_session.commit()

        cat2 = Category(code=888, name="TestCat2", icon="test2", description="Test2")
        db_session.add(cat2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    @pytest.mark.unit
    def test_category_unique_name(self, db_session):
        cat = Category(code=887, name=f"UniqueName_{_uid()}", icon="test", description="Test")
        db_session.add(cat)
        db_session.commit()

        cat2 = Category(code=886, name=cat.name, icon="test2", description="Test2")
        db_session.add(cat2)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestContactModel:

    @pytest.mark.unit
    def test_contact_not_null_name(self, db_session):
        contact = Contact(phone="1234567")
        db_session.add(contact)
        with pytest.raises(IntegrityError):
            db_session.commit()

    @pytest.mark.unit
    def test_contact_phone_is_nullable(self, db_session):
        """Phone is nullable=True in the model, so None is allowed."""
        contact = Contact(name=f"Test_{_uid()}")
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)
        assert contact.phone is None

    @pytest.mark.unit
    def test_contact_default_pending_changes_count(self, db_session):
        contact = Contact(name=f"Test_{_uid()}", phone="1234567")
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)
        assert contact.pending_changes_count == 0

    @pytest.mark.unit
    def test_contact_default_is_verified_false(self, db_session):
        contact = Contact(name=f"Test_{_uid()}", phone="1234567")
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)
        assert contact.is_verified is False

    @pytest.mark.unit
    def test_contact_invalid_category_fk(self, db_session):
        contact = Contact(name=f"Test_{_uid()}", phone="1234567", category_id=99999)
        db_session.add(contact)
        with pytest.raises(IntegrityError):
            db_session.commit()

    @pytest.mark.unit
    def test_contact_valid_category_fk(self, db_session):
        cat = db_session.query(Category).filter_by(code=100).first()
        assert cat is not None
        contact = Contact(name=f"Test_{_uid()}", phone="1234567", category_id=cat.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)
        assert contact.category_id == cat.id

    @pytest.mark.unit
    def test_contact_invalid_user_fk(self, db_session):
        contact = Contact(name=f"Test_{_uid()}", phone="1234567", user_id=99999)
        db_session.add(contact)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestContactHistoryModel:

    @pytest.mark.unit
    def test_history_not_null_contact_id(self, db_session):
        history = ContactHistory(
            user_id=1, field_name="name", old_value="A", new_value="B"
        )
        db_session.add(history)
        with pytest.raises(IntegrityError):
            db_session.commit()

    @pytest.mark.unit
    def test_history_not_null_field_name(self, db_session):
        contact = Contact(name=f"Test_{_uid()}", phone="1234567")
        db_session.add(contact)
        db_session.commit()

        history = ContactHistory(
            contact_id=contact.id, user_id=None, old_value="A", new_value="B"
        )
        db_session.add(history)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestContactChangeModel:

    @pytest.mark.unit
    def test_change_not_null_contact_id(self, db_session):
        change = ContactChange(field_name="name", old_value="A", new_value="B")
        db_session.add(change)
        with pytest.raises(IntegrityError):
            db_session.commit()

    @pytest.mark.unit
    def test_change_not_null_field_name(self, db_session):
        contact = Contact(name=f"Test_{_uid()}", phone="1234567")
        db_session.add(contact)
        db_session.commit()

        change = ContactChange(contact_id=contact.id, old_value="A", new_value="B")
        db_session.add(change)
        with pytest.raises(IntegrityError):
            db_session.commit()

    @pytest.mark.unit
    def test_change_not_null_new_value(self, db_session):
        contact = Contact(name=f"Test_{_uid()}", phone="1234567")
        db_session.add(contact)
        db_session.commit()

        change = ContactChange(
            contact_id=contact.id, field_name="name", old_value="A"
        )
        db_session.add(change)
        with pytest.raises(IntegrityError):
            db_session.commit()

    @pytest.mark.unit
    def test_change_default_is_verified_false(self, db_session):
        contact = Contact(name=f"Test_{_uid()}", phone="1234567")
        db_session.add(contact)
        db_session.commit()

        change = ContactChange(
            contact_id=contact.id, field_name="name", old_value="A", new_value="B"
        )
        db_session.add(change)
        db_session.commit()
        db_session.refresh(change)
        assert change.is_verified is False


class TestPragmaForeignKeys:

    @pytest.mark.unit
    def test_foreign_keys_enabled(self, test_engine):
        from sqlalchemy import text

        with test_engine.connect() as conn:
            result = conn.execute(text("PRAGMA foreign_keys"))
            value = result.fetchone()[0]
            assert value == 1, f"Expected foreign_keys=1, got {value}"
