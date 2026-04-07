"""Deep schema validation tests for ContactCreate and ContactUpdate."""
import pytest
from pydantic import ValidationError
from app.schemas.contact import ContactCreate, ContactUpdate, sanitize_text, validate_phone, validate_url


class TestSanitizeText:
    """Test HTML sanitization function."""

    def test_escapes_angle_brackets(self):
        result = sanitize_text('<script>alert("xss")</script>')
        assert '<' not in result
        assert '>' not in result

    def test_escapes_ampersand(self):
        assert sanitize_text('A & B') == 'A &amp; B'

    def test_escapes_quotes(self):
        result = sanitize_text('say "hello"')
        assert '&quot;' in result

    def test_none_returns_none(self):
        assert sanitize_text(None) is None

    def test_empty_string_unchanged(self):
        assert sanitize_text('') == ''

    def test_normal_text_unchanged(self):
        assert sanitize_text('Hello World') == 'Hello World'

    def test_multiple_special_chars(self):
        result = sanitize_text('<b>"test" & \'more\'</b>')
        assert '&' in result  # Escaped entities present
        assert '<' not in result


class TestValidatePhone:
    """Test phone validation."""

    def test_valid_phone_digits_only(self):
        assert validate_phone('1234567890') == '1234567890'

    def test_valid_phone_with_spaces(self):
        assert validate_phone('123 456 7890') == '123 456 7890'

    def test_valid_phone_with_dashes(self):
        assert validate_phone('123-456-7890') == '123-456-7890'

    def test_valid_phone_with_parens(self):
        assert validate_phone('(0341) 123-4567') == '(0341) 123-4567'

    def test_invalid_phone_with_letters(self):
        with pytest.raises(ValueError, match="solo puede contener"):
            validate_phone('abc1234567')

    def test_invalid_phone_with_semicolon(self):
        with pytest.raises(ValueError):
            validate_phone('1234567; DROP TABLE')

    def test_invalid_phone_with_plus(self):
        with pytest.raises(ValueError):
            validate_phone('+54 341 1234567')

    def test_invalid_phone_with_at_sign(self):
        with pytest.raises(ValueError):
            validate_phone('user@domain')


class TestValidateUrl:
    """Test URL validation."""

    def test_valid_http(self):
        assert validate_url('http://example.com', 'test') == 'http://example.com'

    def test_valid_https(self):
        assert validate_url('https://example.com/path?query=1', 'test') == 'https://example.com/path?query=1'

    def test_none_returns_none(self):
        assert validate_url(None, 'test') is None

    def test_invalid_no_scheme(self):
        with pytest.raises(ValueError, match="http:// o https://"):
            validate_url('example.com', 'test')

    def test_invalid_javascript_scheme(self):
        with pytest.raises(ValueError):
            validate_url('javascript:alert(1)', 'test')

    def test_invalid_file_scheme(self):
        with pytest.raises(ValueError):
            validate_url('file:///etc/passwd', 'test')

    def test_invalid_data_scheme(self):
        with pytest.raises(ValueError):
            validate_url('data:text/html,<script>alert(1)</script>', 'test')


class TestContactCreateValidation:
    """Test ContactCreate schema validators."""

    def test_valid_minimal(self):
        contact = ContactCreate(name="Test", phone="1234567")
        assert contact.name == "Test"
        assert contact.phone == "1234567"

    def test_valid_full(self):
        contact = ContactCreate(
            name="Full Contact",
            phone="1234567",
            email="test@example.com",
            address="Calle 123",
            city="Rosario",
            neighborhood="Centro",
            category_id=100,
            description="A plumber",
            schedule="Lun-Vie 8-18",
            website="https://example.com",
            latitude=-32.95,
            longitude=-60.66,
            maps_url="https://maps.google.com/...",
            instagram="@plumber",
            facebook="https://fb.com/plumber",
            about="Long description here",
        )
        assert contact.email == "test@example.com"
        assert contact.latitude == -32.95

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="A", phone="1234567")

    def test_name_too_long(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="A" * 101, phone="1234567")

    def test_phone_too_short(self):
        """Phone has no min_length in schema, only max_length=20 and format validation."""
        # Short phone is valid — only format is validated (digits, spaces, dashes, parens)
        contact = ContactCreate(name="Test", phone="12345")
        assert contact.phone == "12345"

    def test_phone_too_long(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", phone="1" * 21)

    def test_latitude_out_of_range_high(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", phone="1234567", latitude=91.0)

    def test_latitude_out_of_range_low(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", phone="1234567", latitude=-91.0)

    def test_longitude_out_of_range(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", phone="1234567", longitude=-181.0)

    def test_boundary_latitude_valid(self):
        contact = ContactCreate(name="Test", phone="1234567", latitude=90.0)
        assert contact.latitude == 90.0

    def test_boundary_longitude_valid(self):
        contact = ContactCreate(name="Test", phone="1234567", longitude=-180.0)
        assert contact.longitude == -180.0

    def test_xss_in_name_is_sanitized(self):
        contact = ContactCreate(name="<b>Bold</b>", phone="1234567")
        assert '<' not in contact.name

    def test_xss_in_description_is_sanitized(self):
        contact = ContactCreate(
            name="Test", phone="1234567",
            description="<script>alert('xss')</script>"
        )
        assert '<script>' not in contact.description

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", phone="1234567", email="not-an-email")

    def test_valid_email(self):
        contact = ContactCreate(name="Test", phone="1234567", email="test@example.com")
        assert contact.email == "test@example.com"

    def test_about_max_length(self):
        contact = ContactCreate(name="Test", phone="1234567", about="A" * 2000)
        assert len(contact.about) == 2000

    def test_about_too_long(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", phone="1234567", about="A" * 2001)


class TestContactUpdateValidation:
    """Test ContactUpdate schema validators."""

    def test_all_fields_optional(self):
        contact = ContactUpdate()
        assert contact.name is None
        assert contact.phone is None
        assert contact.email is None

    def test_partial_update(self):
        contact = ContactUpdate(name="New Name")
        assert contact.name == "New Name"
        assert contact.phone is None

    def test_invalid_phone_when_provided(self):
        with pytest.raises(ValidationError):
            ContactUpdate(phone="abc")

    def test_invalid_url_when_provided(self):
        with pytest.raises(ValidationError):
            ContactUpdate(website="javascript:alert(1)")

    def test_valid_update(self):
        contact = ContactUpdate(
            name="Updated",
            phone="9876543",
            email="new@example.com",
        )
        assert contact.name == "Updated"
        assert contact.phone == "9876543"

    def test_xss_sanitization_on_update(self):
        contact = ContactUpdate(name="<img src=x onerror=alert(1)>")
        assert '<' not in contact.name
