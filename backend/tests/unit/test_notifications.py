"""Unit tests for the notifications router and helper functions."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from app.models.notification import Notification
from app.models.push_subscription import PushSubscription
from app.models.user import User
from app.routes.notifications import (
    get_vapid_public_key,
    subscribe_push,
    unsubscribe_push,
    send_push_to_user,
    send_push_to_zone,
    send_push_to_all,
    send_push_to_roles,
    unread_count,
    list_notifications,
    mark_as_read,
    mark_all_as_read,
    cleanup_expired_subscriptions,
)
from app.config import VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, VAPID_CLAIM_EMAIL
from app.rate_limit import limiter


# Mock data for tests
TEST_USER_ID = 1
TEST_USER_EMAIL = "test@example.com"
TEST_ENDPOINT = "https://example.com/push"
TEST_P256DH = "test_p256dh_key"
TEST_AUTH = "test_auth_key"
TEST_CITY = "Test City"
TEST_TITLE = "Test Title"
TEST_BODY = "Test Body"
TEST_URL = "https://example.com"


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = TEST_USER_ID
    user.email = TEST_USER_EMAIL
    user.role = "user"
    return user


@pytest.fixture
def mock_request():
    """Create a mock request for rate limiting."""
    request = MagicMock(spec=Request)
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def mock_subscription():
    """Create a mock push subscription."""
    sub = MagicMock(spec=PushSubscription)
    sub.id = 1
    sub.user_id = TEST_USER_ID
    sub.endpoint = TEST_ENDPOINT
    sub.p256dh = TEST_P256DH
    sub.auth = TEST_AUTH
    sub.latitude = None
    sub.longitude = None
    sub.city = None
    return sub


@pytest.fixture
def mock_notification():
    """Create a mock notification."""
    notif = MagicMock(spec=Notification)
    notif.id = 1
    notif.user_id = TEST_USER_ID
    notif.is_read = False
    notif.created_at = datetime.now()
    return notif


class TestVapidPublicKey:
    """Tests for the VAPID public key endpoint."""

    def test_returns_public_key_when_configured(self):
        """Should return the public key when VAPID_PUBLIC_KEY is set."""
        with patch('app.routes.notifications.VAPID_PUBLIC_KEY', 'test-public-key'):
            result = get_vapid_public_key()
            assert result == {"public_key": "test-public-key"}

    def test_raises_503_when_not_configured(self):
        """Should raise HTTPException 503 when VAPID_PUBLIC_KEY is not set."""
        with patch('app.routes.notifications.VAPID_PUBLIC_KEY', None):
            with pytest.raises(HTTPException) as exc_info:
                get_vapid_public_key()
            assert exc_info.value.status_code == 503
            assert "Push notifications not configured" in exc_info.value.detail


class TestPushSubscription:
    """Tests for push subscription management."""

    def test_subscribe_push_creates_new_subscription(self, mock_db_session, mock_user, mock_request):
        """Should create a new subscription when one doesn't exist."""
        # Setup: no existing subscription
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Execute
        body = MagicMock()
        body.endpoint = TEST_ENDPOINT
        body.keys = {"p256dh": TEST_P256DH, "auth": TEST_AUTH}
        body.latitude = None
        body.longitude = None
        body.city = None

        result = subscribe_push(
            request=mock_request,
            body=body,
            db=mock_db_session,
            user=mock_user
        )

        # Verify
        assert result == {"message": "Suscripción guardada"}
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        # Check that the added object is a PushSubscription with correct attributes
        added_sub = mock_db_session.add.call_args[0][0]
        assert isinstance(added_sub, PushSubscription)
        assert added_sub.user_id == TEST_USER_ID
        assert added_sub.endpoint == TEST_ENDPOINT
        assert added_sub.p256dh == TEST_P256DH
        assert added_sub.auth == TEST_AUTH

    def test_subscribe_push_updates_existing_subscription(self, mock_db_session, mock_user, mock_request):
        """Should update an existing subscription when endpoint matches."""
        # Setup: existing subscription
        existing_sub = MagicMock(spec=PushSubscription)
        mock_db_session.query.return_value.filter.return_value.first.return_value = existing_sub

        # Execute
        body = MagicMock()
        body.endpoint = TEST_ENDPOINT
        body.keys = {"p256dh": TEST_P256DH, "auth": TEST_AUTH}
        body.latitude = 10.0
        body.longitude = 20.0
        body.city = TEST_CITY

        result = subscribe_push(
            request=mock_request,
            body=body,
            db=mock_db_session,
            user=mock_user
        )

        # Verify
        assert result == {"message": "Suscripción guardada"}
        mock_db_session.add.assert_not_called()  # Should not add new
        mock_db_session.commit.assert_called_once()
        # Check that existing subscription was updated
        assert existing_sub.user_id == TEST_USER_ID
        assert existing_sub.p256dh == TEST_P256DH
        assert existing_sub.auth == TEST_AUTH
        assert existing_sub.latitude == 10.0
        assert existing_sub.longitude == 20.0
        assert existing_sub.city == TEST_CITY

    def test_subscribe_push_raises_503_when_vapid_not_configured(self, mock_db_session, mock_user, mock_request):
        """Should raise HTTPException 503 when VAPID_PRIVATE_KEY is not set."""
        with patch('app.routes.notifications.VAPID_PRIVATE_KEY', None):
            body = MagicMock()
            body.endpoint = TEST_ENDPOINT
            body.keys = {"p256dh": TEST_P256DH, "auth": TEST_AUTH}

            with pytest.raises(HTTPException) as exc_info:
                subscribe_push(
                    request=mock_request,
                    body=body,
                    db=mock_db_session,
                    user=mock_user
                )
            assert exc_info.value.status_code == 503
            assert "Push notifications not configured" in exc_info.value.detail

    def test_subscribe_push_raises_400_when_keys_missing(self, mock_db_session, mock_user, mock_request):
        """Should raise HTTPException 400 when p256dh or auth keys are missing."""
        # Test missing p256dh
        body = MagicMock()
        body.endpoint = TEST_ENDPOINT
        body.keys = {"auth": TEST_AUTH}  # missing p256dh

        with pytest.raises(HTTPException) as exc_info:
            subscribe_push(
                request=mock_request,
                body=body,
                db=mock_db_session,
                user=mock_user
            )
        assert exc_info.value.status_code == 400
        assert "Missing keys: p256dh and auth required" in exc_info.value.detail

        # Test missing auth
        body.keys = {"p256dh": TEST_P256DH}  # missing auth

        with pytest.raises(HTTPException) as exc_info:
            subscribe_push(
                request=mock_request,
                body=body,
                db=mock_db_session,
                user=mock_user
            )
        assert exc_info.value.status_code == 400
        assert "Missing keys: p256dh and auth required" in exc_info.value.detail

    def test_unsubscribe_push_removes_subscription(self, mock_db_session, mock_user, mock_request):
        """Should remove the subscription when it exists."""
        # Setup: subscription exists
        mock_db_session.query.return_value.filter.return_value.delete.return_value = 1  # 1 row deleted

        # Execute
        body = MagicMock()
        body.endpoint = TEST_ENDPOINT

        result = unsubscribe_push(
            request=mock_request,
            body=body,
            db=mock_db_session,
            user=mock_user
        )

        # Verify
        assert result == {"message": "Suscripción eliminada"}
        mock_db_session.query.return_value.filter.return_value.delete.assert_called_once_with(
            PushSubscription.endpoint == TEST_ENDPOINT,
            PushSubscription.user_id == TEST_USER_ID
        )
        mock_db_session.commit.assert_called_once()

    def test_unsubscribe_push_returns_not_found_when_not_subscribed(self, mock_db_session, mock_user, mock_request):
        """Should return 'not found' message when no subscription matches."""
        # Setup: no subscription found
        mock_db_session.query.return_value.filter.return_value.delete.return_value = 0  # 0 rows deleted

        # Execute
        body = MagicMock()
        body.endpoint = TEST_ENDPOINT

        result = unsubscribe_push(
            request=mock_request,
            body=body,
            db=mock_db_session,
            user=mock_user
        )

        # Verify
        assert result == {"message": "No encontrada"}
        mock_db_session.commit.assert_called_once()


class TestNotificationEndpoints:
    """Tests for notification-related endpoints."""

    def test_unread_count_returns_correct_count(self, mock_db_session, mock_user):
        """Should return the count of unread notifications."""
        # Setup: 3 unread notifications
        mock_db_session.query.return_value.filter.return_value.count.return_value = 3

        # Execute
        result = unread_count(db=mock_db_session, user=mock_user)

        # Verify
        assert result == {"unread_count": 3}
        mock_db_session.query.return_value.filter.assert_called_once_with(
            Notification.user_id == TEST_USER_ID,
            Notification.is_read == False
        )

    def test_list_notifications_returns_notifications(self, mock_db_session, mock_user, mock_notification):
        """Should return a list of notifications for the user."""
        # Setup: return a list with one notification
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_notification]

        # Execute
        result = list_notifications(db=mock_db_session, user=mock_user)

        # Verify
        assert result == [mock_notification]
        mock_db_session.query.return_value.filter.assert_called_once_with(Notification.user_id == TEST_USER_ID)
        mock_db_session.query.return_value.filter.return_value.order_by.assert_called_once_with(Notification.created_at.desc())
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.assert_called_once_with(50)

    def test_mark_as_read_success(self, mock_db_session, mock_user):
        """Should mark a notification as read when it exists and belongs to user."""
        # Setup: notification exists and belongs to user
        notif = MagicMock(spec=Notification)
        notif.id = 1
        notif.user_id = TEST_USER_ID
        notif.is_read = False
        mock_db_session.query.return_value.filter.return_value.first.return_value = notif

        # Execute
        result = mark_as_read(notification_id=1, db=mock_db_session, user=mock_user)

        # Verify
        assert result == {"message": "Marcada como leída"}
        assert notif.is_read == True
        mock_db_session.commit.assert_called_once()

    def test_mark_as_read_raises_404_when_notification_not_found(self, mock_db_session, mock_user):
        """Should raise HTTPException 404 when notification doesn't exist or doesn't belong to user."""
        # Setup: no notification found
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Execute and verify
        with pytest.raises(HTTPException) as exc_info:
            mark_as_read(notification_id=999, db=mock_db_session, user=mock_user)
        assert exc_info.value.status_code == 404
        assert "Notificación no encontrada" in exc_info.value.detail
        mock_db_session.commit.assert_not_called()

    def test_mark_all_as_read_marks_all_notifications_as_read(self, mock_db_session, mock_user):
        """Should mark all user's notifications as read."""
        # Execute
        result = mark_all_as_read(db=mock_db_session, user=mock_user)

        # Verify
        assert result == {"message": "Todas marcadas como leídas"}
        mock_db_session.query.return_value.filter.return_value.update.assert_called_once_with({"is_read": True})
        mock_db_session.commit.assert_called_once()


class TestAdminEndpoints:
    """Tests for admin endpoints."""

    def test_cleanup_expired_subscriptions_requires_admin_role(self, mock_db_session, mock_user):
        """Should require admin or moderator role."""
        # Setup: user is not admin or moderator
        mock_user.role = "user"

        # Execute and verify
        with pytest.raises(HTTPException) as exc_info:
            cleanup_expired_subscriptions(db=mock_db_session, user=mock_user)
        assert exc_info.value.status_code == 403
        assert "Solo administradores" in exc_info.value.detail

    def test_cleanup_expired_subscriptions_allows_admin_role(self, mock_db_session, mock_user):
        """Should allow admin role."""
        # Setup: user is admin
        mock_user.role = "admin"
        mock_db_session.query.return_value.count.return_value = 42

        # Execute
        result = cleanup_expired_subscriptions(db=mock_db_session, user=mock_user)

        # Verify
        assert result["message"] == "El cleanup automático está habilitado"
        assert result["total_subscriptions"] == 42
        mock_db_session.query.return_value.count.assert_called_once_with(PushSubscription)

    def test_cleanup_expired_subscriptions_allows_moderator_role(self, mock_db_session, mock_user):
        """Should allow moderator role."""
        # Setup: user is moderator
        mock_user.role = "moderator"
        mock_db_session.query.return_value.count.return_value = 10

        # Execute
        result = cleanup_expired_subscriptions(db=mock_db_session, user=mock_user)

        # Verify
        assert result["message"] == "El cleanup automático está habilitado"
        assert result["total_subscriptions"] == 10


class TestPushHelperFunctions:
    """Tests for the push notification helper functions."""

    def test_send_push_to_user_returns_0_when_vapid_not_configured(self, mock_db_session):
        """Should return 0 when VAPID_PRIVATE_KEY is not set."""
        with patch('app.routes.notifications.VAPID_PRIVATE_KEY', None):
            result = send_push_to_user(db=mock_db_session, user_id=TEST_USER_ID, title=TEST_TITLE, body=TEST_BODY)
            assert result == 0

    def test_send_push_to_user_returns_0_when_no_subscriptions(self, mock_db_session):
        """Should return 0 when user has no push subscriptions."""
        with patch('app.routes.notifications.VAPID_PRIVATE_KEY', 'test-key'):
            # Setup: no subscriptions
            mock_db_session.query.return_value.filter.return_value.all.return_value = []

            # Execute
            result = send_push_to_user(db=mock_db_session, user_id=TEST_USER_ID, title=TEST_TITLE, body=TEST_BODY)

            # Verify
            assert result == 0
            mock_db_session.query.return_value.filter.assert_called_once_with(
                PushSubscription.user_id == TEST_USER_ID
            )

    def test_send_push_to_user_handles_webpush_exception_gracefully(self, mock_db_session):
        """Should handle WebPushException and clean up expired subscriptions."""
        with patch('app.routes.notifications.VAPID_PRIVATE_KEY', 'test-key'), \
             patch('app.routes.notifications.webpush') as mock_webpush, \
             patch('app.routes.notifications.logger') as mock_logger:

            # Setup: one subscription that raises WebPushException with 410 status
            sub = MagicMock(spec=PushSubscription)
            sub.id = 1
            mock_db_session.query.return_value.filter.return_value.all.return_value = [sub]

            # Make webpush raise WebPushException with response status 410
            class MockWebPushException(Exception):
                def __init__(self):
                    self.response = MagicMock()
                    self.response.status_code = 410

            mock_webpush.side_effect = MockWebPushException()

            # Execute
            result = send_push_to_user(db=mock_db_session, user_id=TEST_USER_ID, title=TEST_TITLE, body=TEST_BODY)

            # Verify
            assert result == 0  # No successful sends
            mock_db_session.query.return_value.filter.return_value.delete.assert_called_once_with(
                PushSubscription.id.in_([1])
            )
            mock_db_session.commit.assert_called_once()
            mock_logger.info.assert_called_once_with("Push subscription 1 expired (HTTP 410)")

    def test_send_push_to_user_counts_successful_sends(self, mock_db_session):
        """Should count successful sends and not delete non-expired subscriptions."""
        with patch('app.routes.notifications.VAPID_PRIVATE_KEY', 'test-key'), \
             patch('app.routes.notifications.webpush') as mock_webpush:

            # Setup: two subscriptions, both successful
            sub1 = MagicMock(spec=PushSubscription)
            sub1.id = 1
            sub2 = MagicMock(spec=PushSubscription)
            sub2.id = 2
            mock_db_session.query.return_value.filter.return_value.all.return_value = [sub1, sub2]

            # Make webpush succeed (no exception)
            mock_webpush.return_value = None

            # Execute
            result = send_push_to_user(db=mock_db_session, user_id=TEST_USER_ID, title=TEST_TITLE, body=TEST_BODY)

            # Verify
            assert result == 2  # Two successful sends
            mock_db_session.query.return_value.filter.return_value.delete.assert_not_called()
            mock_db_session.commit.assert_not_called()

    def test_send_push_to_zone_handles_missing_city_gracefully(self, mock_db_session):
        """Should work when city is None (send to all zones effectively)."""
        with patch('app.routes.notifications.VAPID_PRIVATE_KEY', 'test-key'), \
             patch('app.routes.notifications.webpush') as mock_webpush:

            # Setup: one subscription
            sub = MagicMock(spec=PushSubscription)
            mock_db_session.query.return_value.filter.return_value.all.return_value = [sub]
            mock_webpush.return_value = None  # successful send

            # Execute
            result = send_push_to_zone(db=mock_db_session, title=TEST_TITLE, body=TEST_BODY, city=None)

            # Verify
            assert result == 1
            mock_db_session.query.return_value.filter.assert_called_once()  # No city filter applied
            mock_db_session.query.return_value.filter.return_value.all.assert_called_once()

    def test_send_push_to_zone_filters_by_city(self, mock_db_session):
        """Should filter subscriptions by city when provided."""
        with patch('app.routes.notifications.VAPID_PRIVATE_KEY', 'test-key'), \
             patch('app.routes.notifications.webpush') as mock_webpush:

            # Setup: two subscriptions, one matching city, one not
            sub1 = MagicMock(spec=PushSubscription)
            sub1.city = "Test City"
            sub2 = MagicMock(spec=PushSubscription)
            sub2.city = "Other City"
            mock_db_session.query.return_value.filter.return_value.all.return_value = [sub1]  # Only sub1 matches
            mock_webpush.return_value = None  # successful send

            # Execute
            result = send_push_to_zone(db=mock_db_session, title=TEST_TITLE, body=TEST_BODY, city="Test City")

            # Verify
            assert result == 1
            # Verify that ilike filter was applied for city
            mock_db_session.query.return_value.filter.assert_any_call(
                PushSubscription.city.ilike(f"%{TEST_CITY}%")
            )

    def test_send_push_to_all_handles_no_subscriptions(self, mock_db_session):
        """Should return 0 when there are no subscriptions at all."""
        with patch('app.routes.notifications.VAPID_PRIVATE_KEY', 'test-key'):
            # Setup: no subscriptions
            mock_db_session.query.return_value.all.return_value = []

            # Execute
            result = send_push_to_all(db=mock_db_session, title=TEST_TITLE, body=TEST_BODY)

            # Verify
            assert result == 0

    def test_send_push_to_roles_returns_0_when_no_users_with_roles(self, mock_db_session):
        """Should return 0 when no users have the specified roles."""
        with patch('app.routes.notifications.VAPID_PRIVATE_KEY', 'test-key'):
            # Setup: no users with roles
            mock_db_session.query.return_value.filter.return_value.all.return_value = []

            # Execute
            result = send_push_to_roles(db=mock_db_session, roles=["admin"], title=TEST_TITLE, body=TEST_BODY)

            # Verify
            assert result == 0

    def test_send_push_to_roles_sends_to_users_with_matching_roles(self, mock_db_session):
        """Should send push notifications to users with specified roles."""
        with patch('app.routes.notifications.VAPID_PRIVATE_KEY', 'test-key'), \
             patch('app.routes.notifications.webpush') as mock_webpush:

            # Setup: two users with admin role, each with one subscription
            user1 = MagicMock(spec=User)
            user1.id = 1
            user2 = MagicMock(spec=User)
            user2.id = 2
            mock_db_session.query.return_value.filter.return_value.all.return_value = [user1, user2]  # users query

            sub1 = MagicMock(spec=PushSubscription)
            sub1.id = 1
            sub1.user_id = 1
            sub2 = MagicMock(spec=PushSubscription)
            sub2.id = 2
            sub2.user_id = 2
            mock_db_session.query.return_value.filter.return_value.all.return_value = [sub1, sub2]  # subscriptions query

            mock_webpush.return_value = None  # successful sends

            # Execute
            result = send_push_to_roles(db=mock_db_session, roles=["admin"], title=TEST_TITLE, body=TEST_BODY)

            # Verify
            assert result == 2  # Two successful sends
            # Verify that we filtered users by role
            mock_db_session.query.return_value.filter.assert_any_call(
                User.role.in_(["admin"])
            )
            # Verify that we got subscriptions for those users
            mock_db_session.query.return_value.filter.assert_any_call(
                PushSubscription.user_id.in_([1, 2])
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])