"""Unit tests for SQLAlchemy model constraints.

Validates that model definitions enforce:
- Foreign key relationships
- Unique constraints
- Nullable constraints
- Default values
- Column types and lengths
"""
import pytest
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.models.category import Category
from app.models.contact import Contact, ContactHistory
from app.models.contact_change import ContactChange


class TestUserModel:

    @pytest.mark.unit
    def test_user_unique_username(self, database_session):
        user1 = User(
            username="unique_user",
            email="a@test.com",
            phone_area_code="0341",
            phone_number="1111111",
            password_hash="hash1",
        )
        database_session.add(user1)
        database_session.commit()

        user2 = User(
            username="unique_user",
            email="b@test.com",
            phone_area_code="0341",
            phone_number="2222222",
            password_hash="hash2",
        )
        database_session.add(user2)
        with pytest.raises(IntegrityError):
            database_session.commit()

    @pytest.mark.unit
    def test_user_unique_email(self, database_session):
        user1 = User(
            username="user_a",
            email="same@test.com",
            phone_area_code="0341",
            phone_number="1111111",
            password_hash="hash1",
        )
        database_session.add(user1)
        database_session.commit()

        user2 = User(
            username="user_b",
            email="same@test.com",
            phone_area_code="0341",
            phone_number="2222222",
            password_hash="hash2",
        )
        database_session.add(user2)
        with pytest.raises(IntegrityError):
            database_session.commit()

    @pytest.mark.unit
    def test_user_default_role_is_user(self, database_session):
        user = User(
            username="default_role",
            email="default@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash="hash",
        )
        database_session.add(user)
        database_session.commit()
        database_session.refresh(user)
        assert user.role == "user"

    @pytest.mark.unit
    def test_user_default_is_active_true(self, database_session):
        user = User(
            username="active_default",
            email="active@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash="hash",
        )
        database_session.add(user)
        database_session.commit()
        database_session.refresh(user)
        assert user.is_active is True

    @pytest.mark.unit
    def test_user_nullable_fields(self, database_session):
        user = User(
            username="no_phone",
            email="nophone@test.com",
            password_hash="hash",
        )
        database_session.add(user)
        with pytest.raises(IntegrityError):
            database_session.commit()


class TestCategoryModel:

    @pytest.mark.unit
    def test_category_unique_code(self, database_session):
        cat = Category(code=888, name="TestCat", icon="test", description="Test")
        database_session.add(cat)
        database_session.commit()

        cat2 = Category(code=888, name="TestCat2", icon="test2", description="Test2")
        database_session.add(cat2)
        with pytest.raises(IntegrityError):
            database_session.commit()

    @pytest.mark.unit
    def test_category_unique_name(self, database_session):
        cat = Category(code=887, name="UniqueName", icon="test", description="Test")
        database_session.add(cat)
        database_session.commit()

        cat2 = Category(code=886, name="UniqueName", icon="test2", description="Test2")
        database_session.add(cat2)
        with pytest.raises(IntegrityError):
            database_session.commit()


class TestContactModel:

    @pytest.mark.unit
    def test_contact_not_null_name(self, database_session):
        contact = Contact(phone="1234567")
        database_session.add(contact)
        with pytest.raises(IntegrityError):
            database_session.commit()

    @pytest.mark.unit
    def test_contact_phone_is_nullable(self, db_session):
        """Phone is nullable=True in the model, so None is allowed."""
        contact = Contact(name="Test")
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)
        assert contact.phone is None

    @pytest.mark.unit
    def test_contact_default_pending_changes_count(self, database_session):
        contact = Contact(name="Test", phone="1234567")
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)
        assert contact.pending_changes_count == 0

    @pytest.mark.unit
    def test_contact_default_is_verified_false(self, database_session):
        contact = Contact(name="Test", phone="1234567")
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)
        assert contact.is_verified is False

    @pytest.mark.unit
    def test_contact_invalid_category_fk(self, database_session):
        contact = Contact(name="Test", phone="1234567", category_id=99999)
        database_session.add(contact)
        with pytest.raises(IntegrityError):
            database_session.commit()

    @pytest.mark.unit
    def test_contact_valid_category_fk(self, database_session):
        cat = database_session.query(Category).filter_by(code=100).first()
        contact = Contact(name="Test", phone="1234567", category_id=cat.id)
        database_session.add(contact)
        database_session.commit()
        database_session.refresh(contact)
        assert contact.category_id == cat.id

    @pytest.mark.unit
    def test_contact_invalid_user_fk(self, database_session):
        contact = Contact(name="Test", phone="1234567", user_id=99999)
        database_session.add(contact)
        with pytest.raises(IntegrityError):
            database_session.commit()


class TestContactHistoryModel:

    @pytest.mark.unit
    def test_history_not_null_contact_id(self, database_session):
        history = ContactHistory(user_id=1, field_name="name", old_value="A", new_value="B")
        database_session.add(history)
        with pytest.raises(IntegrityError):
            database_session.commit()

    @pytest.mark.unit
    def test_history_not_null_field_name(self, database_session):
        contact = Contact(name="Test", phone="1234567")
        database_session.add(contact)
        database_session.commit()

        history = ContactHistory(contact_id=contact.id, user_id=None, old_value="A", new_value="B")
        database_session.add(history)
        with pytest.raises(IntegrityError):
            database_session.commit()


class TestContactChangeModel:

    @pytest.mark.unit
    def test_change_not_null_contact_id(self, database_session):
        change = ContactChange(field_name="name", old_value="A", new_value="B")
        database_session.add(change)
        with pytest.raises(IntegrityError):
            database_session.commit()

    @pytest.mark.unit
    def test_change_not_null_field_name(self, database_session):
        contact = Contact(name="Test", phone="1234567")
        database_session.add(contact)
        database_session.commit()

        change = ContactChange(contact_id=contact.id, old_value="A", new_value="B")
        database_session.add(change)
        with pytest.raises(IntegrityError):
            database_session.commit()

    @pytest.mark.unit
    def test_change_not_null_new_value(self, database_session):
        contact = Contact(name="Test", phone="1234567")
        database_session.add(contact)
        database_session.commit()

        change = ContactChange(contact_id=contact.id, field_name="name", old_value="A")
        database_session.add(change)
        with pytest.raises(IntegrityError):
            database_session.commit()

    @pytest.mark.unit
    def test_change_default_is_verified_false(self, database_session):
        contact = Contact(name="Test", phone="1234567")
        database_session.add(contact)
        database_session.commit()

        change = ContactChange(
            contact_id=contact.id, field_name="name", old_value="A", new_value="B"
        )
        database_session.add(change)
        database_session.commit()
        database_session.refresh(change)
        assert change.is_verified is False


class TestPragmaForeignKeys:

    @pytest.mark.unit
    def test_foreign_keys_enabled(self, test_engine):
        with test_engine.connect() as conn:
            result = conn.exec_driver_sql("PRAGMA foreign_keys")
            value = result.fetchone()[0]
            assert value == 1, f"Expected foreign_keys=1, got {value}"
