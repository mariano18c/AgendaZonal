"""Unit tests for geo utilities, CaptchaManager, ImageService, and PermissionService.

Adapted from tests_ant/unit/test_models_geo_captcha_services.py — uses current conftest fixtures.
Covers:
- Model instantiation for all SQLAlchemy models
- Geo: haversine_km, bounding_box, validate_coordinates
- Captcha: generation, verification, expiration, cleanup
- Image service: resize, save, delete
- Permission service: can_edit_field, can_verify_change
"""
import io
import math
import time
import uuid
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.geo import haversine_km, bounding_box, validate_coordinates, is_within_radius
from app.captcha import CaptchaManager, CaptchaChallenge
from app.services.image_service import resize_image, save_image, delete_image
from app.services.permission_service import can_edit_field, can_verify_change

# Model imports
from app.models.user import User
from app.models.category import Category
from app.models.contact import Contact, ContactHistory
from app.models.review import Review
from app.models.offer import Offer
from app.models.report import Report
from app.models.utility_item import UtilityItem
from app.models.schedule import Schedule
from app.models.contact_photo import ContactPhoto
from app.models.lead_event import LeadEvent
from app.models.notification import Notification
from app.models.push_subscription import PushSubscription
from app.models.contact_change import ContactChange


def _uid():
    return uuid.uuid4().hex[:8]


# ===========================================================================
# MODEL INSTANTIATION TESTS
# ===========================================================================

class TestModelInstantiation:
    """Verify all models can be instantiated with required fields."""

    @pytest.mark.unit
    def test_user_model(self, db_session):
        user = User(
            username=f"user_{_uid()}",
            email=f"u_{_uid()}@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash="hash",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        assert user.id is not None
        assert user.role == "user"
        assert user.is_active is True

    @pytest.mark.unit
    def test_contact_model(self, db_session):
        cat = db_session.query(Category).filter_by(code=100).first()
        assert cat is not None
        contact = Contact(name=f"Contact_{_uid()}", phone="1234567", category_id=cat.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)
        assert contact.id is not None
        assert contact.is_verified is False
        assert contact.pending_changes_count == 0

    @pytest.mark.unit
    def test_review_model(self, db_session, create_user):
        user = create_user(username=f"rev_{_uid()}", email=f"rev_{_uid()}@test.com")
        cat = db_session.query(Category).filter_by(code=100).first()
        contact = Contact(name=f"Review_{_uid()}", phone="1234567", user_id=user.id, category_id=cat.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        review = Review(contact_id=contact.id, user_id=user.id, rating=5, comment="Good", is_approved=False)
        db_session.add(review)
        db_session.commit()
        db_session.refresh(review)
        assert review.id is not None
        assert review.is_approved is False

    @pytest.mark.unit
    def test_offer_model(self, db_session, create_user):
        from datetime import datetime, timedelta, timezone
        user = create_user(username=f"off_{_uid()}", email=f"off_{_uid()}@test.com")
        cat = db_session.query(Category).filter_by(code=100).first()
        contact = Contact(name=f"Offer_{_uid()}", phone="1234567", user_id=user.id, category_id=cat.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        offer = Offer(
            contact_id=contact.id, title="Sale",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_active=True,
        )
        db_session.add(offer)
        db_session.commit()
        db_session.refresh(offer)
        assert offer.id is not None
        assert offer.is_active is True

    @pytest.mark.unit
    def test_report_model(self, db_session, create_user):
        user = create_user(username=f"rep_{_uid()}", email=f"rep_{_uid()}@test.com")
        cat = db_session.query(Category).filter_by(code=100).first()
        contact = Contact(name=f"Report_{_uid()}", phone="1234567", user_id=user.id, category_id=cat.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        report = Report(contact_id=contact.id, user_id=user.id, reason="spam")
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)
        assert report.id is not None
        assert report.is_resolved is False

    @pytest.mark.unit
    def test_utility_item_model(self, db_session):
        item = UtilityItem(name=f"Utility_{_uid()}", type="emergency", phone="123")
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)
        assert item.id is not None
        assert item.is_active is True

    @pytest.mark.unit
    def test_schedule_model(self, db_session, create_user):
        user = create_user(username=f"sch_{_uid()}", email=f"sch_{_uid()}@test.com")
        cat = db_session.query(Category).filter_by(code=100).first()
        contact = Contact(name=f"Schedule_{_uid()}", phone="1234567", user_id=user.id, category_id=cat.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        sched = Schedule(contact_id=contact.id, day_of_week=1, open_time="09:00", close_time="18:00")
        db_session.add(sched)
        db_session.commit()
        db_session.refresh(sched)
        assert sched.id is not None

    @pytest.mark.unit
    def test_contact_photo_model(self, db_session, create_user):
        user = create_user(username=f"ph_{_uid()}", email=f"ph_{_uid()}@test.com")
        cat = db_session.query(Category).filter_by(code=100).first()
        contact = Contact(name=f"Photo_{_uid()}", phone="1234567", user_id=user.id, category_id=cat.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        photo = ContactPhoto(contact_id=contact.id, photo_path="test.jpg", sort_order=1)
        db_session.add(photo)
        db_session.commit()
        db_session.refresh(photo)
        assert photo.id is not None

    @pytest.mark.unit
    def test_lead_event_model(self, db_session, create_user):
        user = create_user(username=f"lead_{_uid()}", email=f"lead_{_uid()}@test.com")
        cat = db_session.query(Category).filter_by(code=100).first()
        contact = Contact(name=f"Lead_{_uid()}", phone="1234567", user_id=user.id, category_id=cat.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        lead = LeadEvent(contact_id=contact.id, source="whatsapp")
        db_session.add(lead)
        db_session.commit()
        db_session.refresh(lead)
        assert lead.id is not None

    @pytest.mark.unit
    def test_notification_model(self, db_session, create_user):
        user = create_user(username=f"notif_{_uid()}", email=f"notif_{_uid()}@test.com")
        notif = Notification(user_id=user.id, type="review", message="Test notification")
        db_session.add(notif)
        db_session.commit()
        db_session.refresh(notif)
        assert notif.id is not None
        assert notif.is_read is False

    @pytest.mark.unit
    def test_push_subscription_model(self, db_session, create_user):
        user = create_user(username=f"push_{_uid()}", email=f"push_{_uid()}@test.com")
        sub = PushSubscription(
            user_id=user.id, endpoint="https://push.example.com/abc",
            p256dh="p256", auth="auth",
        )
        db_session.add(sub)
        db_session.commit()
        db_session.refresh(sub)
        assert sub.id is not None

    @pytest.mark.unit
    def test_contact_change_model(self, db_session, create_user):
        user = create_user(username=f"chg_{_uid()}", email=f"chg_{_uid()}@test.com")
        cat = db_session.query(Category).filter_by(code=100).first()
        contact = Contact(name=f"Change_{_uid()}", phone="1234567", user_id=user.id, category_id=cat.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        change = ContactChange(contact_id=contact.id, field_name="name", old_value="A", new_value="B")
        db_session.add(change)
        db_session.commit()
        db_session.refresh(change)
        assert change.id is not None
        assert change.is_verified is False

    @pytest.mark.unit
    def test_contact_history_model(self, db_session, create_user):
        user = create_user(username=f"hist_{_uid()}", email=f"hist_{_uid()}@test.com")
        cat = db_session.query(Category).filter_by(code=100).first()
        contact = Contact(name=f"History_{_uid()}", phone="1234567", user_id=user.id, category_id=cat.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        hist = ContactHistory(contact_id=contact.id, user_id=user.id, field_name="name", old_value="A", new_value="B")
        db_session.add(hist)
        db_session.commit()
        db_session.refresh(hist)
        assert hist.id is not None


# ===========================================================================
# GEO UTILITIES
# ===========================================================================

class TestHaversineKm:

    @pytest.mark.unit
    def test_same_point_zero_distance(self):
        assert haversine_km(-32.95, -60.65, -32.95, -60.65) == 0.0

    @pytest.mark.unit
    def test_rosario_to_buenos_aires(self):
        """Approximate distance: Rosario to Buenos Aires ~300 km."""
        dist = haversine_km(-32.95, -60.65, -34.60, -58.38)
        assert 270 < dist < 330

    @pytest.mark.unit
    def test_one_km_distance(self):
        """Very short distance should be approximately 1 km."""
        dist = haversine_km(-32.95, -60.65, -32.94, -60.65)
        assert 0.5 < dist < 2.0

    @pytest.mark.unit
    def test_antipodal_points(self):
        """Points on opposite sides of Earth should be ~20,000 km."""
        dist = haversine_km(0, 0, 0, 180)
        assert 19000 < dist < 21000

    @pytest.mark.unit
    def test_pole_to_equator(self):
        """North pole to equator should be ~10,000 km."""
        dist = haversine_km(90, 0, 0, 0)
        assert 9500 < dist < 10500


class TestBoundingBox:

    @pytest.mark.unit
    def test_center_returns_correct_bounds(self):
        bb = bounding_box(-32.95, -60.65, 10)
        assert bb.lat_min == pytest.approx(-32.95 - 10/111, abs=0.01)
        assert bb.lat_max == pytest.approx(-32.95 + 10/111, abs=0.01)

    @pytest.mark.unit
    def test_zero_radius(self):
        bb = bounding_box(-32.95, -60.65, 0)
        assert bb.lat_min == bb.lat_max == -32.95
        assert bb.lon_min == bb.lon_max == -60.65

    @pytest.mark.unit
    def test_large_radius(self):
        bb = bounding_box(-32.95, -60.65, 500)
        assert bb.lat_min < -32.95
        assert bb.lat_max > -32.95
        assert bb.lon_min < -60.65
        assert bb.lon_max > -60.65

    @pytest.mark.unit
    def test_near_pole_north(self):
        bb = bounding_box(89.9, 0, 10)
        assert bb.lat_max <= 90.0

    @pytest.mark.unit
    def test_near_pole_south(self):
        bb = bounding_box(-89.9, 0, 10)
        assert bb.lat_min >= -90.0


class TestValidateCoordinates:

    @pytest.mark.unit
    def test_valid_coords(self):
        assert validate_coordinates(-32.95, -60.65) is True

    @pytest.mark.unit
    def test_both_none(self):
        assert validate_coordinates(None, None) is True

    @pytest.mark.unit
    def test_only_lat_none(self):
        assert validate_coordinates(None, -60.65) is False

    @pytest.mark.unit
    def test_only_lon_none(self):
        assert validate_coordinates(-32.95, None) is False

    @pytest.mark.unit
    def test_lat_out_of_range(self):
        assert validate_coordinates(91, 0) is False
        assert validate_coordinates(-91, 0) is False

    @pytest.mark.unit
    def test_lon_out_of_range(self):
        assert validate_coordinates(0, 181) is False
        assert validate_coordinates(0, -181) is False

    @pytest.mark.unit
    def test_boundary_values(self):
        assert validate_coordinates(90, 180) is True
        assert validate_coordinates(-90, -180) is True
        assert validate_coordinates(0, 0) is True


class TestIsWithinRadius:

    @pytest.mark.unit
    def test_same_point_within(self):
        assert is_within_radius(-32.95, -60.65, -32.95, -60.65, 1) is True

    @pytest.mark.unit
    def test_close_point_within_radius(self):
        assert is_within_radius(-32.95, -60.65, -32.94, -60.65, 5) is True

    @pytest.mark.unit
    def test_far_point_outside_radius(self):
        assert is_within_radius(-32.95, -60.65, -34.60, -58.38, 10) is False


# ===========================================================================
# CAPTCHA MANAGER
# ===========================================================================

class TestCaptchaManager:

    @pytest.fixture(autouse=True)
    def _clear_captchas(self):
        """Clear CAPTCHA challenges before and after each test."""
        CaptchaManager.CHALLENGES.clear()
        yield
        CaptchaManager.CHALLENGES.clear()

    @pytest.mark.unit
    def test_generate_returns_challenge(self):
        challenge = CaptchaManager.generate()
        assert isinstance(challenge, CaptchaChallenge)
        assert challenge.id is not None
        assert challenge.question is not None
        assert challenge.answer_hash is not None

    @pytest.mark.unit
    def test_generate_has_expiration(self):
        challenge = CaptchaManager.generate()
        assert challenge.expires_at > time.time()

    @pytest.mark.unit
    def test_verify_correct_answer(self):
        challenge = CaptchaManager.generate()
        # Extract answer from question
        if ' + ' in challenge.question:
            parts = challenge.question.replace(' = ?', '').split(' + ')
            answer = int(parts[0]) + int(parts[1])
        elif ' - ' in challenge.question:
            parts = challenge.question.replace(' = ?', '').split(' - ')
            answer = int(parts[0]) - int(parts[1])
        else:  # multiplication
            parts = challenge.question.replace(' = ?', '').split(' × ')
            answer = int(parts[0]) * int(parts[1])

        assert CaptchaManager.verify(challenge.id, str(answer)) is True

    @pytest.mark.unit
    def test_verify_wrong_answer(self):
        challenge = CaptchaManager.generate()
        assert CaptchaManager.verify(challenge.id, "999999") is False

    @pytest.mark.unit
    def test_verify_nonexistent_challenge(self):
        assert CaptchaManager.verify("nonexistent-id", "42") is False

    @pytest.mark.unit
    def test_challenge_is_one_time_use(self):
        challenge = CaptchaManager.generate()
        # Extract answer
        if ' + ' in challenge.question:
            parts = challenge.question.replace(' = ?', '').split(' + ')
            answer = int(parts[0]) + int(parts[1])
        elif ' - ' in challenge.question:
            parts = challenge.question.replace(' = ?', '').split(' - ')
            answer = int(parts[0]) - int(parts[1])
        else:
            parts = challenge.question.replace(' = ?', '').split(' × ')
            answer = int(parts[0]) * int(parts[1])

        assert CaptchaManager.verify(challenge.id, str(answer)) is True
        # Second verification should fail (challenge removed)
        assert CaptchaManager.verify(challenge.id, str(answer)) is False

    @pytest.mark.unit
    def test_expired_challenge(self):
        challenge = CaptchaManager.generate()
        # Manually expire it
        challenge.expires_at = time.time() - 1
        assert CaptchaManager.verify(challenge.id, "0") is False


# ===========================================================================
# IMAGE SERVICE
# ===========================================================================

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

    @pytest.mark.unit
    def test_exact_max_size(self):
        img = Image.new("RGB", (1024, 1024), color="white")
        resized = resize_image(img, (1024, 1024))
        assert resized.width == 1024
        assert resized.height == 1024


class TestSaveImage:

    @pytest.mark.unit
    def test_save_image_returns_path(self, tmp_path):
        """Test save_image with a temporary directory."""
        with patch("app.services.image_service.UPLOAD_DIR", tmp_path):
            # Create a valid JPEG in memory
            img_buffer = io.BytesIO()
            img = Image.new("RGB", (100, 100), color="blue")
            img.save(img_buffer, format="JPEG")
            img_buffer.seek(0)
            content = img_buffer.getvalue()

            path = save_image(1, content)
            assert path == "/uploads/images/contact_1.jpg"
            assert (tmp_path / "contact_1.jpg").exists()

    @pytest.mark.unit
    def test_save_image_overwrites_existing(self, tmp_path):
        with patch("app.services.image_service.UPLOAD_DIR", tmp_path):
            img_buffer = io.BytesIO()
            img = Image.new("RGB", (100, 100), color="blue")
            img.save(img_buffer, format="JPEG")
            img_buffer.seek(0)

            save_image(1, img_buffer.getvalue())
            # Save again
            img_buffer2 = io.BytesIO()
            img2 = Image.new("RGB", (100, 100), color="red")
            img2.save(img_buffer2, format="JPEG")
            img_buffer2.seek(0)
            save_image(1, img_buffer2.getvalue())

            # File should still exist (overwritten)
            assert (tmp_path / "contact_1.jpg").exists()


class TestDeleteImage:

    @pytest.mark.unit
    def test_delete_existing_image(self, tmp_path):
        with patch("app.services.image_service.UPLOAD_DIR", tmp_path):
            # Create file
            (tmp_path / "contact_1.jpg").write_bytes(b"fake jpeg data")
            assert delete_image(1) is True
            assert not (tmp_path / "contact_1.jpg").exists()

    @pytest.mark.unit
    def test_delete_nonexistent_image(self, tmp_path):
        with patch("app.services.image_service.UPLOAD_DIR", tmp_path):
            assert delete_image(999) is False


# ===========================================================================
# PERMISSION SERVICE
# ===========================================================================

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
