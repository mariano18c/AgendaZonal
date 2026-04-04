"""Parametrized unit tests for Pydantic schemas.

Covers all validation rules with boundary values, valid data, and invalid data.
"""
import pytest
from pydantic import ValidationError
from app.schemas.contact import ContactCreate, ContactUpdate
from app.schemas.auth import RegisterRequest
from app.schemas.user import UserCreate, UserUpdate, UserRoleUpdate, PasswordReset


class TestContactCreateSchema:

    @pytest.mark.parametrize("name,should_pass", [
        ("AB", True),
        ("A" * 100, True),
        ("Juan Perez", True),
        ("A", False),
        ("", False),
        ("A" * 101, False),
    ])
    @pytest.mark.unit
    def test_name_boundaries(self, name: str, should_pass: bool):
        if should_pass:
            contact = ContactCreate(name=name, phone="1234567")
            assert contact.name == name
        else:
            with pytest.raises(ValidationError):
                ContactCreate(name=name, phone="1234567")

    @pytest.mark.parametrize("phone,should_pass", [
        ("12345", True),
        ("123456", True),
        ("12345678901234567890", True),
        ("341-1234567", True),
        ("(0341) 123-4567", True),
        ("1" * 21, False),
        ("abc123", False),
        ("phone<script>", False),
    ])
    @pytest.mark.unit
    def test_phone_boundaries(self, phone: str, should_pass: bool):
        if should_pass:
            contact = ContactCreate(name="Test", phone=phone)
            assert contact.phone == phone
        else:
            with pytest.raises(ValidationError):
                ContactCreate(name="Test", phone=phone)

    @pytest.mark.parametrize("email,should_pass", [
        ("test@test.com", True),
        ("user@domain.org.ar", True),
        (None, True),
        ("noemail", False),
        ("@nodomain.com", False),
        ("user@", False),
    ])
    @pytest.mark.unit
    def test_email_validation(self, email, should_pass: bool):
        if should_pass:
            contact = ContactCreate(name="Test", phone="1234567", email=email)
            assert contact.email == email
        else:
            with pytest.raises(ValidationError):
                ContactCreate(name="Test", phone="1234567", email=email)

    @pytest.mark.parametrize("lat,should_pass", [
        (0.0, True),
        (-90.0, True),
        (90.0, True),
        (-34.6, True),
        (-90.01, False),
        (90.01, False),
        (None, True),
    ])
    @pytest.mark.unit
    def test_latitude_boundaries(self, lat, should_pass: bool):
        if should_pass:
            contact = ContactCreate(name="Test", phone="1234567", latitude=lat)
            assert contact.latitude == lat
        else:
            with pytest.raises(ValidationError):
                ContactCreate(name="Test", phone="1234567", latitude=lat)

    @pytest.mark.parametrize("lng,should_pass", [
        (0.0, True),
        (-180.0, True),
        (180.0, True),
        (-60.63, True),
        (-180.01, False),
        (180.01, False),
        (None, True),
    ])
    @pytest.mark.unit
    def test_longitude_boundaries(self, lng, should_pass: bool):
        if should_pass:
            contact = ContactCreate(name="Test", phone="1234567", longitude=lng)
            assert contact.longitude == lng
        else:
            with pytest.raises(ValidationError):
                ContactCreate(name="Test", phone="1234567", longitude=lng)

    @pytest.mark.parametrize("website,should_pass", [
        ("https://example.com", True),
        ("http://example.com", True),
        (None, True),
        ("example.com", False),
        ("ftp://example.com", False),
        ("javascript:alert(1)", False),
    ])
    @pytest.mark.unit
    def test_website_url_validation(self, website, should_pass: bool):
        if should_pass:
            contact = ContactCreate(name="Test", phone="1234567", website=website)
            assert contact.website == website
        else:
            with pytest.raises(ValidationError):
                ContactCreate(name="Test", phone="1234567", website=website)

    @pytest.mark.parametrize("url,should_pass", [
        ("https://maps.google.com/?q=-34.6,-58.38", True),
        ("http://maps.google.com", True),
        (None, True),
        ("maps.google.com", False),
        ("javascript:alert(1)", False),
    ])
    @pytest.mark.unit
    def test_maps_url_validation(self, url, should_pass: bool):
        if should_pass:
            contact = ContactCreate(name="Test", phone="1234567", maps_url=url)
            assert contact.maps_url == url
        else:
            with pytest.raises(ValidationError):
                ContactCreate(name="Test", phone="1234567", maps_url=url)

    @pytest.mark.unit
    def test_description_max_length(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", phone="1234567", description="X" * 501)

    @pytest.mark.unit
    def test_description_at_limit(self):
        contact = ContactCreate(name="Test", phone="1234567", description="X" * 500)
        assert len(contact.description) == 500

    @pytest.mark.unit
    def test_minimal_valid(self):
        contact = ContactCreate(name="AB", phone="123456")
        assert contact.name == "AB"
        assert contact.phone == "123456"
        assert contact.email is None
        assert contact.category_id is None

    @pytest.mark.unit
    def test_full_valid(self):
        contact = ContactCreate(
            name="Juan Perez",
            phone="(0341) 123-4567",
            email="juan@test.com",
            address="Calle Falsa 123",
            city="Rosario",
            neighborhood="Centro",
            category_id=100,
            description="Plomero matriculado",
            schedule="Lun-Vie 8:00-18:00",
            website="https://plomero.com",
            latitude=-32.95,
            longitude=-60.63,
            maps_url="https://maps.google.com/?q=-32.95,-60.63",
        )
        assert contact.city == "Rosario"
        assert contact.latitude == -32.95


class TestContactUpdateSchema:

    @pytest.mark.unit
    def test_empty_update_allowed(self):
        update = ContactUpdate()
        assert update.name is None

    @pytest.mark.unit
    def test_partial_update(self):
        update = ContactUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.phone is None

    @pytest.mark.unit
    def test_update_validates_constraints(self):
        with pytest.raises(ValidationError):
            ContactUpdate(name="A")

    @pytest.mark.unit
    def test_update_phone_validation(self):
        with pytest.raises(ValidationError):
            ContactUpdate(phone="abc")

    @pytest.mark.unit
    def test_update_website_validation(self):
        with pytest.raises(ValidationError):
            ContactUpdate(website="no-scheme.com")


class TestRegisterRequestSchema:

    @pytest.mark.parametrize("password,should_pass", [
        ("password123", True),
        ("12345678", True),
        ("a" * 100, True),
        ("short", False),
        ("1234567", False),
        ("", False),
    ])
    @pytest.mark.unit
    def test_password_boundaries(self, password: str, should_pass: bool):
        if should_pass:
            reg = RegisterRequest(
                username="testuser",
                email="test@test.com",
                phone_area_code="0341",
                phone_number="1234567",
                password=password,
            )
            assert reg.password == password
        else:
            with pytest.raises(ValidationError):
                RegisterRequest(
                    username="testuser",
                    email="test@test.com",
                    phone_area_code="0341",
                    phone_number="1234567",
                    password=password,
                )

    @pytest.mark.parametrize("username,should_pass", [
        ("abc", True),
        ("a" * 50, True),
        ("ab", False),
        ("a" * 51, False),
        ("", False),
    ])
    @pytest.mark.unit
    def test_username_boundaries(self, username: str, should_pass: bool):
        if should_pass:
            reg = RegisterRequest(
                username=username,
                email="test@test.com",
                phone_area_code="0341",
                phone_number="1234567",
                password="password123",
            )
            assert reg.username == username
        else:
            with pytest.raises(ValidationError):
                RegisterRequest(
                    username=username,
                    email="test@test.com",
                    phone_area_code="0341",
                    phone_number="1234567",
                    password="password123",
                )


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

    @pytest.mark.unit
    def test_invalid_role_accepted_by_schema(self):
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
