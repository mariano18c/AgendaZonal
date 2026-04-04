"""Unit tests for Pydantic schemas — Contact CRUD validation."""
import pytest
from pydantic import ValidationError

from app.schemas.contact import (
    ContactCreate,
    ContactUpdate,
    ContactResponse,
    ContactChangeCreate,
    ScheduleEntry,
    sanitize_text,
    validate_phone,
    validate_url,
)


class TestContactCreateSchema:
    """Validate ContactCreate schema constraints."""

    def test_valid_minimal_contact(self):
        """Only name is required."""
        contact = ContactCreate(name="Juan Pérez")
        assert contact.name == "Juan Pérez"
        assert contact.phone is None

    def test_valid_full_contact(self):
        """All fields populated with valid data."""
        contact = ContactCreate(
            name="Juan Pérez Plomero",
            phone="1234567",
            email="juan@test.com",
            address="Calle Falsa 123",
            city="Rosario",
            neighborhood="Centro",
            category_id=1,
            description="Plomero con 20 años de experiencia",
            latitude=-32.9442,
            longitude=-60.6505,
            instagram="@juanplomero",
            facebook="https://facebook.com/juanplomero",
            about="Descripción larga del negocio",
        )
        assert contact.name == "Juan Pérez Plomero"
        assert contact.latitude == -32.9442

    def test_name_too_short(self):
        """Name must be at least 2 characters."""
        with pytest.raises(ValidationError):
            ContactCreate(name="A")

    def test_name_too_long(self):
        """Name max 100 characters."""
        with pytest.raises(ValidationError):
            ContactCreate(name="A" * 101)

    def test_invalid_email(self):
        """Email must be valid format."""
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", email="not-an-email")

    def test_invalid_phone_with_letters(self):
        """Phone cannot contain letters."""
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", phone="abc123")

    def test_valid_phone_with_special_chars(self):
        """Phone can contain digits, spaces, dashes, parentheses."""
        contact = ContactCreate(name="Test", phone="(0341) 123-4567")
        assert contact.phone == "(0341) 123-4567"

    def test_invalid_website_no_protocol(self):
        """Website must start with http:// or https://."""
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", website="www.example.com")

    def test_valid_website_with_https(self):
        contact = ContactCreate(name="Test", website="https://example.com")
        assert contact.website == "https://example.com"

    def test_invalid_maps_url(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", maps_url="maps.google.com/xyz")

    def test_latitude_out_of_range_negative(self):
        """Latitude must be >= -90."""
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", latitude=-91.0)

    def test_latitude_out_of_range_positive(self):
        """Latitude must be <= 90."""
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", latitude=91.0)

    def test_longitude_out_of_range(self):
        """Longitude must be between -180 and 180."""
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", longitude=181.0)

    def test_description_max_length(self):
        """Description max 500 characters."""
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", description="A" * 501)

    def test_about_max_length(self):
        """About max 2000 characters."""
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", about="A" * 2001)

    def test_html_sanitization_in_name(self):
        """HTML tags should be escaped in name."""
        contact = ContactCreate(name="<script>alert('xss')</script>")
        assert "<script>" not in contact.name
        assert "&lt;script&gt;" in contact.name

    def test_html_sanitization_in_description(self):
        """HTML tags should be escaped in description."""
        contact = ContactCreate(name="Test", description="<b>Bold</b>")
        assert "<b>" not in contact.description
        assert "&lt;b&gt;" in contact.description

    def test_unicode_characters_preserved(self):
        """Unicode characters should be preserved after sanitization."""
        contact = ContactCreate(name="Ñoño García 日本語 🔧")
        assert "Ñoño García 日本語 🔧" in contact.name


class TestContactUpdateSchema:
    """Validate ContactUpdate schema — all fields optional."""

    def test_all_fields_optional(self):
        """Empty update should be valid."""
        update = ContactUpdate()
        assert update.name is None

    def test_partial_update(self):
        """Only updating name should work."""
        update = ContactUpdate(name="Nuevo Nombre")
        assert update.name == "Nuevo Nombre"

    def test_invalid_phone_in_update(self):
        with pytest.raises(ValidationError):
            ContactUpdate(phone="abc")

    def test_name_min_length_in_update(self):
        with pytest.raises(ValidationError):
            ContactUpdate(name="A")

    def test_html_sanitization_in_update(self):
        update = ContactUpdate(description="<img src=x>")
        assert "<img" not in update.description


class TestContactChangeCreateSchema:
    """Validate ContactChangeCreate schema."""

    def test_valid_change(self):
        change = ContactChangeCreate(field_name="description", new_value="Nuevo valor")
        assert change.field_name == "description"

    def test_html_sanitization_in_new_value(self):
        change = ContactChangeCreate(field_name="name", new_value="<script>alert(1)</script>")
        assert "<script>" not in change.new_value


class TestScheduleEntrySchema:
    """Validate ScheduleEntry schema."""

    def test_valid_schedule(self):
        entry = ScheduleEntry(day_of_week=1, open_time="09:00", close_time="18:00")
        assert entry.day_of_week == 1

    def test_day_of_week_boundary_min(self):
        entry = ScheduleEntry(day_of_week=0, open_time="08:00", close_time="17:00")
        assert entry.day_of_week == 0

    def test_day_of_week_boundary_max(self):
        entry = ScheduleEntry(day_of_week=6, open_time="10:00", close_time="14:00")
        assert entry.day_of_week == 6

    def test_day_of_week_negative(self):
        with pytest.raises(ValidationError):
            ScheduleEntry(day_of_week=-1, open_time="09:00", close_time="18:00")

    def test_day_of_week_too_high(self):
        with pytest.raises(ValidationError):
            ScheduleEntry(day_of_week=7, open_time="09:00", close_time="18:00")

    def test_nullable_times(self):
        """Closed day — times can be null."""
        entry = ScheduleEntry(day_of_week=0, open_time=None, close_time=None)
        assert entry.open_time is None


class TestSanitizeTextFunction:
    """Test the sanitize_text utility function."""

    def test_none_returns_none(self):
        assert sanitize_text(None) is None

    def test_plain_text_unchanged(self):
        assert sanitize_text("Hello World") == "Hello World"

    def test_escapes_less_than(self):
        assert sanitize_text("<div>") == "&lt;div&gt;"

    def test_escapes_greater_than(self):
        assert sanitize_text("</div>") == "&lt;/div&gt;"

    def test_escapes_ampersand(self):
        assert sanitize_text("Tom & Jerry") == "Tom &amp; Jerry"

    def test_escapes_quotes(self):
        result = sanitize_text('He said "hello"')
        assert "&quot;" in result

    def test_escapes_script_tag(self):
        result = sanitize_text("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestValidatePhoneFunction:
    """Test the validate_phone utility function."""

    def test_none_returns_none(self):
        assert validate_phone(None) is None

    def test_empty_string_returns_none(self):
        assert validate_phone("") is None

    def test_whitespace_only_returns_none(self):
        assert validate_phone("   ") is None

    def test_valid_digits_only(self):
        assert validate_phone("1234567") == "1234567"

    def test_valid_with_spaces_and_dashes(self):
        assert validate_phone("123-456 7890") == "123-456 7890"

    def test_valid_with_parentheses(self):
        assert validate_phone("(0341) 123-4567") == "(0341) 123-4567"

    def test_invalid_with_letters(self):
        with pytest.raises(ValueError):
            validate_phone("abc123")

    def test_invalid_with_special_chars(self):
        with pytest.raises(ValueError):
            validate_phone("123@456")


class TestValidateUrlFunction:
    """Test the validate_url utility function."""

    def test_none_returns_none(self):
        assert validate_url(None, "url") is None

    def test_valid_http(self):
        assert validate_url("http://example.com", "url") == "http://example.com"

    def test_valid_https(self):
        assert validate_url("https://example.com", "url") == "https://example.com"

    def test_invalid_no_protocol(self):
        with pytest.raises(ValueError):
            validate_url("example.com", "url")

    def test_invalid_ftp(self):
        with pytest.raises(ValueError):
            validate_url("ftp://example.com", "url")
