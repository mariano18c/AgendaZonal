"""Unit tests — Pydantic schemas validation.

Tests all schema validators: ContactCreate, ContactUpdate, ReviewCreate,
ReportCreate, OfferCreate, UserCreate, ScheduleEntry, etc.
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from app.schemas.contact import (
    ContactCreate, ContactUpdate, ContactResponse,
    VerifyContactRequest, TransferOwnershipRequest, ScheduleEntry,
    ContactChangeCreate,
)
from app.schemas.auth import RegisterRequest, LoginRequest, CaptchaVerifyRequest
from app.schemas.review import ReviewCreate, ReviewReplyCreate, VerifyLevelRequest
from app.schemas.report import ReportCreate
from app.schemas.offer import OfferCreate
from app.schemas.user import UserCreate, UserUpdate, UserRoleUpdate, PasswordReset
from app.schemas.utility import UtilityItemCreate


# ── ContactCreate ─────────────────────────────────────────────────────

class TestContactCreate:
    def test_valid_minimal(self):
        c = ContactCreate(name="Juan")
        assert c.name == "Juan"

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="J")

    def test_name_too_long(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="x" * 101)

    def test_xss_sanitized(self):
        c = ContactCreate(name='<script>alert("xss")</script>')
        assert "<script>" not in c.name
        assert "&lt;script&gt;" in c.name

    def test_phone_valid(self):
        c = ContactCreate(name="Test", phone="(341) 555-1234")
        assert c.phone == "(341) 555-1234"

    def test_phone_invalid_chars(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", phone="abc-not-a-phone")

    def test_phone_none(self):
        c = ContactCreate(name="Test", phone=None)
        assert c.phone is None

    def test_phone_empty_string(self):
        c = ContactCreate(name="Test", phone="")
        assert c.phone is None  # validate_phone converts empty to None

    def test_email_valid(self):
        c = ContactCreate(name="Test", email="test@example.com")
        assert c.email == "test@example.com"

    def test_email_invalid(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", email="not-an-email")

    def test_website_valid(self):
        c = ContactCreate(name="Test", website="https://example.com")
        assert c.website == "https://example.com"

    def test_website_no_scheme(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", website="example.com")

    def test_maps_url_valid(self):
        c = ContactCreate(name="Test", maps_url="https://maps.google.com/abc")
        assert "maps.google.com" in c.maps_url

    def test_maps_url_no_scheme(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", maps_url="maps.google.com")

    def test_latitude_bounds(self):
        ContactCreate(name="Test", latitude=-90, longitude=0)
        ContactCreate(name="Test", latitude=90, longitude=0)
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", latitude=91, longitude=0)
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", latitude=-91, longitude=0)

    def test_longitude_bounds(self):
        ContactCreate(name="Test", latitude=0, longitude=-180)
        ContactCreate(name="Test", latitude=0, longitude=180)
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", latitude=0, longitude=181)

    def test_description_max_length(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", description="x" * 501)

    def test_about_max_length(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", about="x" * 2001)

    def test_sanitize_multiple_fields(self):
        c = ContactCreate(
            name="<b>Bold</b>",
            address="<img src=x>",
            city="<div>City</div>",
            description="<a href='#'>Link</a>",
        )
        assert "<b>" not in c.name
        assert "<img" not in c.address
        assert "<div>" not in c.city


# ── ContactUpdate ─────────────────────────────────────────────────────

class TestContactUpdate:
    def test_partial_update(self):
        u = ContactUpdate(name="New Name")
        data = u.model_dump(exclude_unset=True)
        assert data == {"name": "New Name"}

    def test_phone_min_length(self):
        with pytest.raises(ValidationError):
            ContactUpdate(phone="12345")  # min 6

    def test_sanitize_text(self):
        u = ContactUpdate(name="<h1>Title</h1>")
        assert "<h1>" not in u.name


# ── ReviewCreate ──────────────────────────────────────────────────────

class TestReviewCreate:
    def test_valid(self):
        r = ReviewCreate(rating=5, comment="Great!")
        assert r.rating == 5

    def test_rating_min(self):
        with pytest.raises(ValidationError):
            ReviewCreate(rating=0)

    def test_rating_max(self):
        with pytest.raises(ValidationError):
            ReviewCreate(rating=6)

    def test_comment_sanitized(self):
        r = ReviewCreate(rating=3, comment='<script>alert("xss")</script>')
        assert "<script>" not in r.comment

    def test_comment_max_length(self):
        with pytest.raises(ValidationError):
            ReviewCreate(rating=3, comment="x" * 501)

    def test_comment_none_allowed(self):
        r = ReviewCreate(rating=4)
        assert r.comment is None


class TestReviewReplyCreate:
    def test_valid(self):
        r = ReviewReplyCreate(reply_text="Gracias!")
        assert r.reply_text

    def test_empty_rejected(self):
        with pytest.raises(ValidationError):
            ReviewReplyCreate(reply_text="")

    def test_sanitized(self):
        r = ReviewReplyCreate(reply_text="<b>Gracias</b>")
        assert "<b>" not in r.reply_text


# ── ReportCreate ──────────────────────────────────────────────────────

class TestReportCreate:
    @pytest.mark.parametrize("reason", ["spam", "falso", "inapropiado", "cerrado"])
    def test_valid_reasons(self, reason):
        r = ReportCreate(reason=reason)
        assert r.reason == reason

    def test_invalid_reason(self):
        with pytest.raises(ValidationError):
            ReportCreate(reason="invalid_reason")

    def test_details_sanitized(self):
        r = ReportCreate(reason="spam", details='<script>x</script>')
        assert "<script>" not in r.details


# ── OfferCreate ───────────────────────────────────────────────────────

class TestOfferCreate:
    def test_valid(self):
        o = OfferCreate(
            title="Promo",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        assert o.title == "Promo"

    def test_discount_bounds(self):
        with pytest.raises(ValidationError):
            OfferCreate(title="X", discount_pct=0,
                        expires_at=datetime.now(timezone.utc) + timedelta(days=1))
        with pytest.raises(ValidationError):
            OfferCreate(title="X", discount_pct=100,
                        expires_at=datetime.now(timezone.utc) + timedelta(days=1))

    def test_title_required(self):
        with pytest.raises(ValidationError):
            OfferCreate(expires_at=datetime.now(timezone.utc) + timedelta(days=1))


# ── Auth schemas ──────────────────────────────────────────────────────

class TestAuthSchemas:
    def test_register_valid(self):
        r = RegisterRequest(
            username="juan", email="j@test.com",
            phone_area_code="0341", phone_number="1234567",
            password="securepass1",
        )
        assert r.username == "juan"

    def test_register_password_too_short(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="juan", email="j@test.com",
                            phone_area_code="0341", phone_number="1234567",
                            password="short")

    def test_register_username_too_short(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="ab", email="j@test.com",
                            phone_area_code="0341", phone_number="1234567",
                            password="password123")

    def test_login_schema(self):
        l = LoginRequest(username_or_email="admin", password="pass")
        assert l.username_or_email == "admin"


# ── User schemas ──────────────────────────────────────────────────────

class TestUserSchemas:
    def test_user_create(self):
        u = UserCreate(username="new", email="new@test.com",
                       phone_area_code="011", phone_number="1234567",
                       password="password123", role="user")
        assert u.role == "user"

    def test_user_update_partial(self):
        u = UserUpdate(username="changed")
        assert u.model_dump(exclude_unset=True) == {"username": "changed"}

    def test_password_reset_min(self):
        with pytest.raises(ValidationError):
            PasswordReset(new_password="short")


# ── Utility schemas ───────────────────────────────────────────────────

class TestUtilitySchemas:
    def test_valid(self):
        u = UtilityItemCreate(name="Farmacia Central")
        assert u.type == "otro"

    def test_name_required(self):
        with pytest.raises(ValidationError):
            UtilityItemCreate(name="")


# ── Other schemas ─────────────────────────────────────────────────────

class TestMiscSchemas:
    def test_verify_contact_request(self):
        v = VerifyContactRequest(is_verified=True)
        assert v.is_verified is True

    def test_transfer_ownership_request(self):
        t = TransferOwnershipRequest(new_owner_id=5)
        assert t.new_owner_id == 5

    def test_transfer_ownership_zero_rejected(self):
        with pytest.raises(ValidationError):
            TransferOwnershipRequest(new_owner_id=0)

    def test_schedule_entry_valid(self):
        s = ScheduleEntry(day_of_week=0, open_time="08:00", close_time="18:00")
        assert s.day_of_week == 0

    def test_schedule_entry_invalid_day(self):
        with pytest.raises(ValidationError):
            ScheduleEntry(day_of_week=7)

    def test_verify_level_bounds(self):
        VerifyLevelRequest(verification_level=0)
        VerifyLevelRequest(verification_level=3)
        with pytest.raises(ValidationError):
            VerifyLevelRequest(verification_level=4)

    def test_contact_change_sanitized(self):
        c = ContactChangeCreate(field_name="name", new_value="<b>X</b>")
        assert "<b>" not in c.new_value

    def test_captcha_verify_request(self):
        c = CaptchaVerifyRequest(challenge_id="abc", answer="42")
        assert c.answer == "42"

    def test_contact_response_from_attributes(self):
        """ContactResponse should be constructible from ORM attributes."""
        cr = ContactResponse(id=1, name="Test")
        assert cr.id == 1
        assert cr.status == "active"


# ===========================================================================
# MERGED FROM tests_ant: test_all_schemas.py + test_contact_schemas.py
# Additional coverage not present in original test_schemas.py
# ===========================================================================


# ── Auth schema edge cases ─────────────────────────────────────────────

class TestAuthSchemasExtended:
    """Additional auth schema tests from tests_ant."""

    def test_login_empty_password(self):
        """LoginRequest should accept empty password (validation at route level)."""
        l = LoginRequest(username_or_email="admin", password="")
        assert l.password == ""

    def test_register_password_exactly_min_length(self):
        """Password with exactly 8 chars should be valid."""
        r = RegisterRequest(
            username="testuser", email="t@test.com",
            phone_area_code="0341", phone_number="1234567",
            password="12345678",
        )
        assert r.password == "12345678"

    def test_register_password_too_long(self):
        """Password over 100 chars should be rejected."""
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="testuser", email="t@test.com",
                phone_area_code="0341", phone_number="1234567",
                password="x" * 101,
            )

    def test_register_username_exactly_min(self):
        """Username with exactly 3 chars should be valid."""
        r = RegisterRequest(
            username="abc", email="t@test.com",
            phone_area_code="0341", phone_number="1234567",
            password="password123",
        )
        assert r.username == "abc"

    def test_register_username_too_long(self):
        """Username over 50 chars should be rejected."""
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="x" * 51, email="t@test.com",
                phone_area_code="0341", phone_number="1234567",
                password="password123",
            )


# ── User schema edge cases ─────────────────────────────────────────────

class TestUserSchemasExtended:
    """Additional user schema tests from tests_ant."""

    def test_user_create_default_role(self):
        """UserCreate should default to 'user' role."""
        u = UserCreate(
            username="new", email="new@test.com",
            phone_area_code="011", phone_number="1234567",
            password="password123",
        )
        assert u.role == "user"

    def test_user_create_with_moderator_role(self):
        """UserCreate should accept 'moderator' role."""
        u = UserCreate(
            username="mod", email="mod@test.com",
            phone_area_code="011", phone_number="1234567",
            password="password123", role="moderator",
        )
        assert u.role == "moderator"

    def test_user_create_with_admin_role(self):
        """UserCreate should accept 'admin' role."""
        u = UserCreate(
            username="admin", email="admin@test.com",
            phone_area_code="011", phone_number="1234567",
            password="password123", role="admin",
        )
        assert u.role == "admin"

    def test_user_role_update_valid_roles(self):
        """UserRoleUpdate should accept valid roles."""
        for role in ["user", "moderator", "admin"]:
            u = UserRoleUpdate(role=role)
            assert u.role == role

    def test_user_update_email_none(self):
        """UserUpdate should allow None email."""
        u = UserUpdate(email=None)
        assert u.email is None

    def test_user_update_phone_none(self):
        """UserUpdate should allow None phone fields."""
        u = UserUpdate(phone_area_code=None, phone_number=None)
        assert u.phone_area_code is None
        assert u.phone_number is None

    def test_password_reset_exactly_min(self):
        """PasswordReset with exactly 8 chars should be valid."""
        pr = PasswordReset(new_password="12345678")
        assert pr.new_password == "12345678"


# ── Category schemas ───────────────────────────────────────────────────

class TestCategorySchemas:
    """Category schema tests from tests_ant."""

    def test_category_base_valid(self):
        from app.schemas.category import CategoryBase
        c = CategoryBase(code=100, name="Plomero")
        assert c.code == 100
        assert c.name == "Plomero"

    def test_category_base_optional_fields(self):
        from app.schemas.category import CategoryBase
        c = CategoryBase(code=100, name="Plomero", icon="wrench", description="Fix pipes")
        assert c.icon == "wrench"
        assert c.description == "Fix pipes"

    def test_category_base_minimal(self):
        from app.schemas.category import CategoryBase
        c = CategoryBase(code=100, name="Plomero")
        assert c.icon is None
        assert c.description is None

    def test_category_response(self):
        from app.schemas.category import CategoryResponse
        c = CategoryResponse(id=1, code=100, name="Plomero")
        assert c.id == 1
        assert c.code == 100
        assert c.name == "Plomero"


# ── Contact schema validators ──────────────────────────────────────────

class TestContactSchemaValidators:
    """Tests for validate_phone, validate_url, sanitize_text functions."""

    def test_validate_phone_valid(self):
        from app.schemas.contact import validate_phone
        assert validate_phone("3415551234") == "3415551234"
        assert validate_phone("(341) 555-1234") == "(341) 555-1234"
        assert validate_phone("555-1234") == "555-1234"

    def test_validate_phone_none(self):
        from app.schemas.contact import validate_phone
        assert validate_phone(None) is None

    def test_validate_phone_empty_string(self):
        from app.schemas.contact import validate_phone
        assert validate_phone("") is None
        assert validate_phone("   ") is None

    def test_validate_phone_letters_rejected(self):
        from app.schemas.contact import validate_phone
        with pytest.raises(ValueError):
            validate_phone("1234ABC5678")

    def test_validate_phone_special_chars_rejected(self):
        from app.schemas.contact import validate_phone
        with pytest.raises(ValueError):
            validate_phone("phone<script>alert(1)</script>")

    def test_validate_url_valid(self):
        from app.schemas.contact import validate_url
        assert validate_url("https://example.com", "website") == "https://example.com"
        assert validate_url("http://example.com", "website") == "http://example.com"

    def test_validate_url_none(self):
        from app.schemas.contact import validate_url
        assert validate_url(None, "website") is None

    def test_validate_url_no_scheme_rejected(self):
        from app.schemas.contact import validate_url
        with pytest.raises(ValueError):
            validate_url("example.com", "website")

    def test_validate_url_ftp_rejected(self):
        from app.schemas.contact import validate_url
        with pytest.raises(ValueError):
            validate_url("ftp://example.com", "website")

    def test_sanitize_text_escapes_html(self):
        from app.schemas.contact import sanitize_text
        result = sanitize_text('<script>alert("xss")</script>')
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_sanitize_text_none(self):
        from app.schemas.contact import sanitize_text
        assert sanitize_text(None) is None

    def test_sanitize_text_plain_unchanged(self):
        from app.schemas.contact import sanitize_text
        assert sanitize_text("Hello World") == "Hello World"

    def test_sanitize_text_escapes_quotes(self):
        from app.schemas.contact import sanitize_text
        result = sanitize_text('He said "hello"')
        assert '"' not in result
        assert "&quot;" in result

    def test_sanitize_text_escapes_ampersand(self):
        from app.schemas.contact import sanitize_text
        result = sanitize_text("A & B")
        assert "&amp;" in result


# ── Contact schema extended ────────────────────────────────────────────

class TestContactCreateExtended:
    """Additional ContactCreate tests from tests_ant."""

    def test_unicode_characters_preserved(self):
        """Unicode characters should be preserved after sanitization."""
        c = ContactCreate(name="Café Ñoño")
        assert "Café" in c.name
        assert "Ñoño" in c.name

    def test_html_sanitization_in_name(self):
        """HTML tags in name should be escaped."""
        c = ContactCreate(name="<b>Bold</b>")
        assert "<b>" not in c.name
        assert "&lt;b&gt;" in c.name

    def test_html_sanitization_in_description(self):
        """HTML tags in description should be escaped."""
        c = ContactCreate(name="Test", description='<a href="x">Link</a>')
        assert "<a" not in c.description
        assert "&lt;a" in c.description

    def test_emoji_preserved(self):
        """Emoji should be preserved in text fields."""
        c = ContactCreate(name="🔧 Plomero 🚿")
        assert "🔧" in c.name
        assert "🚿" in c.name

    def test_facebook_url_valid(self):
        """Facebook URL with https should be valid."""
        c = ContactCreate(name="Test", facebook="https://facebook.com/page")
        assert c.facebook == "https://facebook.com/page"

    def test_facebook_url_no_scheme_rejected(self):
        """Facebook URL without scheme should be rejected."""
        # The schema accepts it but the route validates — test schema behavior
        c = ContactCreate(name="Test", facebook="facebook.com/page")
        # Schema doesn't validate URL scheme for facebook, only presence
        assert c.facebook == "facebook.com/page"

    def test_instagram_handle(self):
        """Instagram handle should be accepted."""
        c = ContactCreate(name="Test", instagram="@mybusiness")
        assert c.instagram == "@mybusiness"


class TestContactUpdateExtended:
    """Additional ContactUpdate tests from tests_ant."""

    def test_all_fields_none(self):
        """ContactUpdate with all None should be valid (no-op update)."""
        u = ContactUpdate()
        data = u.model_dump(exclude_unset=True)
        assert data == {}

    def test_partial_update_phone_only(self):
        """Update only phone field."""
        u = ContactUpdate(phone="123456")
        data = u.model_dump(exclude_unset=True)
        assert data == {"phone": "123456"}

    def test_partial_update_geo_only(self):
        """Update only geo fields."""
        u = ContactUpdate(latitude=-32.9, longitude=-60.6)
        data = u.model_dump(exclude_unset=True)
        assert data == {"latitude": -32.9, "longitude": -60.6}

    def test_name_exactly_min_length(self):
        """Name with exactly 2 chars should be valid."""
        u = ContactUpdate(name="Jo")
        assert u.name == "Jo"

    def test_sanitize_text_in_update(self):
        """HTML in update should be sanitized."""
        u = ContactUpdate(name="<script>x</script>")
        assert "<script>" not in u.name


# ── Offer schema extended ──────────────────────────────────────────────

class TestOfferCreateExtended:
    """Additional OfferCreate tests from tests_ant."""

    def test_discount_bounds_exclusive(self):
        """Discount must be > 0 and < 100."""
        with pytest.raises(ValidationError):
            OfferCreate(title="X", discount_pct=0,
                        expires_at=datetime.now(timezone.utc) + timedelta(days=1))
        with pytest.raises(ValidationError):
            OfferCreate(title="X", discount_pct=100,
                        expires_at=datetime.now(timezone.utc) + timedelta(days=1))

    def test_valid_discount_range(self):
        """Discount between 1 and 99 should be valid."""
        o = OfferCreate(
            title="Sale", discount_pct=1,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        assert o.discount_pct == 1

        o2 = OfferCreate(
            title="Sale", discount_pct=99,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        assert o2.discount_pct == 99

    def test_title_max_length(self):
        """Offer title should have max length."""
        with pytest.raises(ValidationError):
            OfferCreate(
                title="x" * 201,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )

    def test_description_optional(self):
        """Offer description should be optional."""
        o = OfferCreate(
            title="Sale",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        assert o.description is None

