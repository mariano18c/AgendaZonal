"""Unit tests for Auth, Review, Offer, Report, User schemas."""
import pytest
from pydantic import ValidationError
from datetime import datetime, timezone, timedelta

from app.schemas.auth import (
    CaptchaChallengeResponse,
    CaptchaVerifyRequest,
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    UserResponse,
)
from app.schemas.review import (
    ReviewCreate,
    ReviewReplyCreate,
    ReviewResponse,
    ReviewListResponse,
    VerifyLevelRequest,
)
from app.schemas.offer import OfferCreate, OfferResponse
from app.schemas.report import ReportCreate, ReportResponse
from app.schemas.user import UserCreate, UserUpdate, UserRoleUpdate, PasswordReset
from app.schemas.category import CategoryBase, CategoryResponse


# ---------------------------------------------------------------------------
# Auth Schemas
# ---------------------------------------------------------------------------

class TestRegisterRequest:
    """Validate registration schema."""

    def test_valid_registration(self):
        req = RegisterRequest(
            username="testuser",
            email="test@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password="securepass123",
        )
        assert req.username == "testuser"

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="test")

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="test", email="not-email",
                phone_area_code="0341", phone_number="123", password="pass123",
            )


class TestLoginRequest:
    """Validate login schema."""

    def test_valid_login(self):
        req = LoginRequest(username_or_email="user@test.com", password="pass123")
        assert req.username_or_email == "user@test.com"

    def test_empty_password_accepted_by_schema(self):
        """BUG: LoginRequest schema does not enforce min_length on password.
        
        The schema accepts empty passwords — validation happens at route level.
        This test documents the gap; fix in schema: Field(min_length=1).
        """
        req = LoginRequest(username_or_email="user", password="")
        assert req.password == ""


class TestCaptchaSchemas:
    """Validate CAPTCHA schemas."""

    def test_captcha_challenge_response(self):
        resp = CaptchaChallengeResponse(challenge_id="abc123", question="2 + 3 = ?")
        assert resp.challenge_id == "abc123"

    def test_captcha_verify_request(self):
        req = CaptchaVerifyRequest(challenge_id="abc123", answer="5")
        assert req.answer == "5"


# ---------------------------------------------------------------------------
# Review Schemas
# ---------------------------------------------------------------------------

class TestReviewCreate:
    """Validate review creation schema."""

    def test_valid_review(self):
        review = ReviewCreate(rating=5, comment="Excellent!")
        assert review.rating == 5

    def test_rating_minimum(self):
        with pytest.raises(ValidationError):
            ReviewCreate(rating=0, comment="Bad")

    def test_rating_maximum(self):
        with pytest.raises(ValidationError):
            ReviewCreate(rating=6, comment="Too high")

    def test_valid_ratings(self):
        for r in [1, 2, 3, 4, 5]:
            review = ReviewCreate(rating=r, comment="OK")
            assert review.rating == r

    def test_comment_too_long(self):
        with pytest.raises(ValidationError):
            ReviewCreate(rating=3, comment="A" * 501)

    def test_html_escaping_in_comment(self):
        review = ReviewCreate(rating=4, comment="<script>alert('xss')</script>")
        assert "<script>" not in review.comment
        assert "&lt;script&gt;" in review.comment

    def test_comment_nullable(self):
        review = ReviewCreate(rating=5)
        assert review.comment is None


class TestReviewReplyCreate:
    """Validate review reply schema."""

    def test_valid_reply(self):
        reply = ReviewReplyCreate(reply_text="Thank you for your feedback!")
        assert "Thank you" in reply.reply_text

    def test_reply_too_long(self):
        with pytest.raises(ValidationError):
            ReviewReplyCreate(reply_text="A" * 501)

    def test_reply_html_escaped(self):
        reply = ReviewReplyCreate(reply_text="<b>Bold</b>")
        assert "<b>" not in reply.reply_text

    def test_reply_too_short(self):
        """Reply must be at least 1 character."""
        with pytest.raises(ValidationError):
            ReviewReplyCreate(reply_text="")


class TestVerifyLevelRequest:
    """Validate verification level schema."""

    def test_valid_levels(self):
        for level in [0, 1, 2, 3]:
            req = VerifyLevelRequest(verification_level=level)
            assert req.verification_level == level

    def test_invalid_level_negative(self):
        with pytest.raises(ValidationError):
            VerifyLevelRequest(verification_level=-1)

    def test_invalid_level_too_high(self):
        with pytest.raises(ValidationError):
            VerifyLevelRequest(verification_level=4)


# ---------------------------------------------------------------------------
# Offer Schemas
# ---------------------------------------------------------------------------

class TestOfferCreate:
    """Validate offer creation schema."""

    def test_valid_offer(self):
        offer = OfferCreate(
            title="Summer Sale",
            description="20% off everything",
            discount_pct=20,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        assert offer.title == "Summer Sale"

    def test_discount_pct_minimum(self):
        with pytest.raises(ValidationError):
            OfferCreate(
                title="Test",
                discount_pct=0,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )

    def test_discount_pct_maximum(self):
        with pytest.raises(ValidationError):
            OfferCreate(
                title="Test",
                discount_pct=100,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )

    def test_valid_discount_boundaries(self):
        for d in [1, 50, 99]:
            offer = OfferCreate(
                title="Test",
                discount_pct=d,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            assert offer.discount_pct == d

    def test_title_required(self):
        with pytest.raises(ValidationError):
            OfferCreate(
                discount_pct=10,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )


# ---------------------------------------------------------------------------
# Report Schemas
# ---------------------------------------------------------------------------

class TestReportCreate:
    """Validate report creation schema."""

    def test_valid_report(self):
        report = ReportCreate(reason="spam", details="This is spam")
        assert report.reason == "spam"

    def test_valid_reasons(self):
        for reason in ["spam", "falso", "inapropiado", "cerrado"]:
            report = ReportCreate(reason=reason)
            assert report.reason == reason

    def test_invalid_reason(self):
        with pytest.raises(ValidationError):
            ReportCreate(reason="otro")

    def test_details_too_long(self):
        with pytest.raises(ValidationError):
            ReportCreate(reason="spam", details="A" * 501)

    def test_details_html_escaped(self):
        report = ReportCreate(reason="spam", details="<script>alert(1)</script>")
        assert "<script>" not in report.details


# ---------------------------------------------------------------------------
# User Schemas
# ---------------------------------------------------------------------------

class TestUserCreate:
    """Validate user creation schema."""

    def test_valid_user(self):
        user = UserCreate(
            username="testuser",
            email="test@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password="securepass123",
            role="user",
        )
        assert user.username == "testuser"

    def test_valid_roles(self):
        for role in ["user", "moderator", "admin"]:
            user = UserCreate(
                username="test", email="t@t.com",
                phone_area_code="0341", phone_number="123456",
                password="pass1234", role=role,
            )
            assert user.role == role

    def test_invalid_role(self):
        """BUG: UserCreate schema does NOT validate role values.
        
        Any string is accepted as role — validation happens at route level.
        This is a security gap; fix: add @field_validator for role.
        """
        # Schema accepts any role — route-level validation catches it
        user = UserCreate(
            username="test", email="t@t.com",
            phone_area_code="0341", phone_number="123456",
            password="pass1234", role="superadmin",
        )
        assert user.role == "superadmin"  # Schema allows it — bug documented


class TestPasswordReset:
    """Validate password reset schema."""

    def test_valid_password(self):
        reset = PasswordReset(new_password="newSecurePass123!")
        assert reset.new_password == "newSecurePass123!"

    def test_password_too_short(self):
        with pytest.raises(ValidationError):
            PasswordReset(new_password="short")

    def test_password_too_long(self):
        with pytest.raises(ValidationError):
            PasswordReset(new_password="A" * 101)


class TestUserRoleUpdate:
    """Validate role update schema."""

    def test_valid_role_update(self):
        update = UserRoleUpdate(role="moderator")
        assert update.role == "moderator"

    def test_invalid_role_update(self):
        """BUG: UserRoleUpdate schema does NOT validate role values.
        
        Any string is accepted — validation happens at route level.
        """
        update = UserRoleUpdate(role="invalid_role")
        assert update.role == "invalid_role"  # Schema allows it — bug documented


# ---------------------------------------------------------------------------
# Category Schemas
# ---------------------------------------------------------------------------

class TestCategorySchemas:
    """Validate category schemas."""

    def test_category_base(self):
        cat = CategoryBase(code=100, name="Plomero", icon="wrench")
        assert cat.code == 100

    def test_category_response(self):
        cat = CategoryResponse(id=1, code=100, name="Plomero", icon="wrench")
        assert cat.id == 1
        assert cat.name == "Plomero"
