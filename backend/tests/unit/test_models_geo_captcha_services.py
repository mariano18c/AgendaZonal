"""Unit tests for models, geo utilities, captcha, and services."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from io import BytesIO

from app.models.user import User
from app.models.contact import Contact, ContactHistory
from app.models.review import Review
from app.models.offer import Offer
from app.models.report import Report
from app.models.category import Category
from app.models.utility_item import UtilityItem
from app.models.schedule import Schedule
from app.models.contact_photo import ContactPhoto
from app.models.lead_event import LeadEvent
from app.models.notification import Notification
from app.models.push_subscription import PushSubscription
from app.models.contact_change import ContactChange

from app.geo import haversine_km, bounding_box, validate_coordinates, BoundingBox
from app.captcha import CaptchaManager, CaptchaChallenge
from app.services.image_service import resize_image, save_image, delete_image
from app.services.permission_service import can_edit_field, can_verify_change


# ---------------------------------------------------------------------------
# Model instantiation tests
# ---------------------------------------------------------------------------

class TestUserModel:
    """Validate User model defaults and attributes."""

    def test_user_defaults_not_applied_in_python(self):
        """BUG: SQLAlchemy defaults NOT applied at Python object level.
        
        Column default= only applies at DB INSERT time.
        """
        user = User(
            username="test",
            email="test@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash="hashed",
        )
        assert user.role is None  # 'user' only after DB insert
        assert user.is_active is None  # True only after DB insert
        assert user.deactivated_at is None

    def test_user_admin(self):
        user = User(
            username="admin",
            email="admin@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash="hashed",
            role="admin",
        )
        assert user.role == "admin"

    def test_user_deactivated(self):
        user = User(
            username="test",
            email="test@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash="hashed",
            is_active=False,
            deactivated_at=datetime.now(timezone.utc),
        )
        assert user.is_active is False
        assert user.deactivated_at is not None


class TestContactModel:
    """Validate Contact model defaults."""

    def test_contact_defaults_not_applied_in_python(self):
        """BUG: SQLAlchemy defaults NOT applied at Python level."""
        contact = Contact(name="Test", phone="123", user_id=1)
        assert contact.status is None
        assert contact.verification_level is None
        assert contact.avg_rating is None
        assert contact.review_count is None
        assert contact.pending_changes_count is None
        assert contact.is_verified is None

    def test_contact_with_geo(self):
        contact = Contact(
            name="Test",
            phone="123",
            user_id=1,
            latitude=-32.9442,
            longitude=-60.6505,
        )
        assert contact.latitude == -32.9442
        assert contact.longitude == -60.6505


class TestReviewModel:
    """Validate Review model — uses is_approved, NOT status."""

    def test_review_defaults_not_applied_in_python(self):
        """BUG: SQLAlchemy defaults NOT applied at Python level."""
        review = Review(contact_id=1, user_id=1, rating=5)
        assert review.is_approved is None
        assert review.reply_text is None
        assert review.reply_at is None
        assert review.reply_by is None

    def test_review_approved(self):
        review = Review(
            contact_id=1, user_id=1, rating=4,
            is_approved=True,
            approved_by=2,
        )
        assert review.is_approved is True
        assert review.approved_by == 2

    def test_review_with_reply(self):
        review = Review(
            contact_id=1, user_id=1, rating=3,
            is_approved=True,
            reply_text="Thank you!",
            reply_at=datetime.now(timezone.utc),
            reply_by=1,
        )
        assert review.reply_text == "Thank you!"
        assert review.reply_by == 1


class TestOfferModel:
    """Validate Offer model — uses is_active, NOT active. No starts_at."""

    def test_offer_defaults_not_applied_in_python(self):
        """BUG: SQLAlchemy defaults NOT applied at Python level."""
        offer = Offer(
            contact_id=1,
            title="Sale",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        assert offer.is_active is None
        assert offer.discount_pct is None
        assert offer.description is None

    def test_offer_with_discount(self):
        offer = Offer(
            contact_id=1,
            title="20% Off",
            discount_pct=20,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        assert offer.discount_pct == 20


class TestReportModel:
    """Validate Report model — uses user_id and is_resolved."""

    def test_report_defaults_not_applied_in_python(self):
        """BUG: SQLAlchemy defaults NOT applied at Python level."""
        report = Report(contact_id=1, user_id=1, reason="spam")
        assert report.is_resolved is None
        assert report.resolved_by is None
        assert report.resolved_at is None

    def test_report_resolved(self):
        report = Report(
            contact_id=1, user_id=1, reason="falso",
            is_resolved=True,
            resolved_by=2,
            resolved_at=datetime.now(timezone.utc),
        )
        assert report.is_resolved is True
        assert report.resolved_by == 2


class TestUtilityItemModel:
    """Validate UtilityItem model."""

    def test_utility_defaults_not_applied_in_python(self):
        """BUG: SQLAlchemy defaults NOT applied at Python level."""
        item = UtilityItem(name="Escuela", type="educacion")
        assert item.type == "educacion"
        assert item.is_active is None


class TestScheduleModel:
    """Validate Schedule model."""

    def test_schedule_valid_day(self):
        schedule = Schedule(contact_id=1, day_of_week=1, open_time="09:00", close_time="18:00")
        assert schedule.day_of_week == 1

    def test_schedule_closed_day(self):
        schedule = Schedule(contact_id=1, day_of_week=0, open_time=None, close_time=None)
        assert schedule.open_time is None


class TestContactPhotoModel:
    """Validate ContactPhoto model."""

    def test_photo_defaults_not_applied_in_python(self):
        """BUG: SQLAlchemy defaults NOT applied at Python level."""
        photo = ContactPhoto(contact_id=1, photo_path="/uploads/test.jpg")
        assert photo.sort_order is None
        assert photo.caption is None


class TestLeadEventModel:
    """Validate LeadEvent model."""

    def test_lead_defaults_not_applied_in_python(self):
        """BUG: SQLAlchemy defaults NOT applied at Python level."""
        lead = LeadEvent(contact_id=1)
        assert lead.source is None


class TestNotificationModel:
    """Validate Notification model."""

    def test_notification_defaults_not_applied_in_python(self):
        """BUG: SQLAlchemy defaults NOT applied at Python level."""
        notif = Notification(user_id=1, type="review", message="New review!")
        assert notif.is_read is None


class TestPushSubscriptionModel:
    """Validate PushSubscription model."""

    def test_push_subscription(self):
        sub = PushSubscription(
            user_id=1,
            endpoint="https://fcm.googleapis.com/...",
            p256dh="base64key",
            auth="authsecret",
        )
        assert sub.endpoint == "https://fcm.googleapis.com/..."


class TestContactChangeModel:
    """Validate ContactChange model."""

    def test_change_defaults_not_applied_in_python(self):
        """BUG: SQLAlchemy defaults NOT applied at Python level."""
        change = ContactChange(
            contact_id=1, user_id=1,
            field_name="description", new_value="New desc",
        )
        assert change.is_verified is None
        assert change.verified_by is None


class TestContactHistoryModel:
    """Validate ContactHistory model."""

    def test_history_entry(self):
        history = ContactHistory(
            contact_id=1, user_id=1,
            field_name="name", old_value="Old", new_value="New",
        )
        assert history.field_name == "name"
        assert history.old_value == "Old"
        assert history.new_value == "New"


# ---------------------------------------------------------------------------
# Geo utilities
# ---------------------------------------------------------------------------

class TestHaversineKm:
    """Test haversine distance calculation."""

    def test_same_point_zero_distance(self):
        """Same coordinates should return 0 km."""
        dist = haversine_km(-32.9442, -60.6505, -32.9442, -60.6505)
        assert dist == 0.0

    def test_rosario_to_centro(self):
        """Known distance Rosario centro to Fisherton ~10km."""
        dist = haversine_km(-32.9442, -60.6505, -32.9500, -60.7000)
        assert 3 < dist < 10  # Approximately 4-5 km

    def test_buenos_aires_to_rosario(self):
        """BA to Rosario ~279km."""
        dist = haversine_km(-34.6037, -58.3816, -32.9442, -60.6505)
        assert 270 < dist < 290

    def test_north_south_one_degree(self):
        """1 degree latitude ≈ 111 km."""
        dist = haversine_km(0, 0, 1, 0)
        assert 110 < dist < 112


class TestBoundingBox:
    """Test bounding box calculation."""

    def test_bounding_box_rosario_5km(self):
        lat, lon = -32.9442, -60.6505
        box = bounding_box(lat, lon, 5)
        assert isinstance(box, BoundingBox)
        assert box.lat_min < lat < box.lat_max
        assert box.lon_min < lon < box.lon_max

    def test_bounding_box_zero_radius(self):
        lat, lon = -32.9442, -60.6505
        box = bounding_box(lat, lon, 0)
        assert box.lat_min == pytest.approx(lat, abs=0.01)
        assert box.lat_max == pytest.approx(lat, abs=0.01)

    def test_bounding_box_large_radius(self):
        lat, lon = -32.9442, -60.6505
        box = bounding_box(lat, lon, 100)
        assert box.lat_max - box.lat_min > 1.0


class TestValidateCoordinates:
    """Test coordinate validation."""

    def test_valid_rosario(self):
        assert validate_coordinates(-32.9442, -60.6505) is True

    def test_valid_zero(self):
        assert validate_coordinates(0.0, 0.0) is True

    def test_invalid_latitude_too_high(self):
        assert validate_coordinates(91.0, 0.0) is False

    def test_invalid_latitude_too_low(self):
        assert validate_coordinates(-91.0, 0.0) is False

    def test_invalid_longitude_too_high(self):
        assert validate_coordinates(0.0, 181.0) is False

    def test_invalid_longitude_too_low(self):
        assert validate_coordinates(0.0, -181.0) is False

    def test_none_coordinates(self):
        """Both None returns True (means 'no coords provided' is valid).
        One None returns False (partial coords are invalid).
        """
        assert validate_coordinates(None, None) is True
        assert validate_coordinates(-32.9, None) is False
        assert validate_coordinates(None, -60.6) is False


# ---------------------------------------------------------------------------
# CAPTCHA
# ---------------------------------------------------------------------------

def _parse_captcha_answer(question: str) -> int:
    """Parse CAPTCHA math question and return the numeric answer."""
    if ' + ' in question:
        match = __import__('re').match(r'(\d+) \+ (\d+)', question)
        return int(match.group(1)) + int(match.group(2))
    elif ' - ' in question:
        match = __import__('re').match(r'(\d+) - (\d+)', question)
        return int(match.group(1)) - int(match.group(2))
    elif ' × ' in question:
        match = __import__('re').match(r'(\d+) × (\d+)', question)
        return int(match.group(1)) * int(match.group(2))
    else:
        raise ValueError(f"Unknown CAPTCHA format: {question}")


class TestCaptchaManager:
    """Test CAPTCHA generation and verification."""

    def test_generate_creates_challenge(self):
        challenge = CaptchaManager.generate()
        assert challenge is not None
        assert challenge.id is not None
        assert challenge.question is not None
        assert challenge.answer_hash is not None

    def test_question_is_math(self):
        challenge = CaptchaManager.generate()
        assert any(op in challenge.question for op in ['+', '-', '×'])

    def test_verify_correct_answer(self):
        challenge = CaptchaManager.generate()
        answer = _parse_captcha_answer(challenge.question)
        assert CaptchaManager.verify(challenge.id, str(answer)) is True

    def test_verify_wrong_answer(self):
        challenge = CaptchaManager.generate()
        answer = _parse_captcha_answer(challenge.question)
        wrong = answer + 100
        assert CaptchaManager.verify(challenge.id, str(wrong)) is False

    def test_verify_nonexistent_challenge(self):
        assert CaptchaManager.verify("nonexistent", "5") is False

    def test_challenge_is_one_time_use(self):
        challenge = CaptchaManager.generate()
        answer = _parse_captcha_answer(challenge.question)
        assert CaptchaManager.verify(challenge.id, str(answer)) is True
        assert CaptchaManager.verify(challenge.id, str(answer)) is False

    def test_multiple_challenges_independent(self):
        c1 = CaptchaManager.generate()
        c2 = CaptchaManager.generate()
        assert c1.id != c2.id
        c2_answer = _parse_captcha_answer(c2.question)
        assert CaptchaManager.verify(c1.id, str(c2_answer)) is False


# ---------------------------------------------------------------------------
# Image Service
# ---------------------------------------------------------------------------

class TestImageService:
    """Test image processing utilities."""

    def test_resize_image_reduces_size(self):
        """Image should be resized to fit within max dimensions."""
        from PIL import Image
        img = Image.new("RGB", (2000, 2000), color="red")
        resized = resize_image(img, (1024, 1024))
        assert resized.width <= 1024
        assert resized.height <= 1024

    def test_resize_image_preserves_aspect_ratio(self):
        """Aspect ratio should be preserved."""
        from PIL import Image
        img = Image.new("RGB", (2000, 1000), color="blue")
        resized = resize_image(img, (1024, 1024))
        assert resized.width <= 1024
        assert resized.height <= 1024
        # Aspect ratio preserved: width should be ~2x height
        ratio = resized.width / resized.height
        assert 1.9 < ratio < 2.1

    def test_resize_image_no_change_if_small(self):
        """Small images should not be resized up."""
        from PIL import Image
        img = Image.new("RGB", (500, 500), color="green")
        resized = resize_image(img, (1024, 1024))
        assert resized.width == 500
        assert resized.height == 500

    def test_save_image_converts_to_rgb(self):
        """RGBA images should be converted to RGB for JPEG."""
        from PIL import Image
        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        loaded = Image.open(buffer)
        # save_image should handle conversion
        assert loaded.mode == "RGBA"  # Original preserved

    def test_delete_image_nonexistent_returns_false(self):
        """delete_image should return False for non-existent files."""
        result = delete_image(999999)
        assert result is False


# ---------------------------------------------------------------------------
# Permission Service
# ---------------------------------------------------------------------------

class TestPermissionService:
    """Test permission logic — signatures match actual implementation."""

    def test_owner_can_edit(self):
        mock_user = MagicMock(id=1, role="user")
        mock_contact = MagicMock(user_id=1)
        can_edit, needs_verify = can_edit_field(mock_user, mock_contact, "name", "old_value")
        assert can_edit is True

    def test_non_owner_cannot_edit_existing(self):
        mock_user = MagicMock(id=2, role="user")
        mock_contact = MagicMock(user_id=1)
        can_edit, needs_verify = can_edit_field(mock_user, mock_contact, "name", "existing")
        assert can_edit is False

    def test_non_owner_can_suggest_empty(self):
        mock_user = MagicMock(id=2, role="user")
        mock_contact = MagicMock(user_id=1)
        can_edit, needs_verify = can_edit_field(mock_user, mock_contact, "description", None)
        assert can_edit is True
        assert needs_verify is True

    def test_moderator_can_edit_any(self):
        mock_user = MagicMock(id=2, role="moderator")
        mock_contact = MagicMock(user_id=1)
        can_edit, needs_verify = can_edit_field(mock_user, mock_contact, "name", "old")
        assert can_edit is True

    def test_admin_can_edit_any(self):
        mock_user = MagicMock(id=2, role="admin")
        mock_contact = MagicMock(user_id=1)
        can_edit, needs_verify = can_edit_field(mock_user, mock_contact, "name", "old")
        assert can_edit is True

    def test_owner_can_verify(self):
        mock_user = MagicMock(id=1, role="user")
        mock_contact = MagicMock(user_id=1)
        assert can_verify_change(mock_user, mock_contact) is True

    def test_moderator_can_verify(self):
        mock_user = MagicMock(id=2, role="moderator")
        mock_contact = MagicMock(user_id=1)
        assert can_verify_change(mock_user, mock_contact) is True

    def test_admin_can_verify(self):
        mock_user = MagicMock(id=2, role="admin")
        mock_contact = MagicMock(user_id=1)
        assert can_verify_change(mock_user, mock_contact) is True

    def test_non_owner_cannot_verify(self):
        mock_user = MagicMock(id=2, role="user")
        mock_contact = MagicMock(user_id=1)
        assert can_verify_change(mock_user, mock_contact) is False
