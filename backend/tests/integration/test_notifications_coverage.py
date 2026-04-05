"""Integration tests — Notifications endpoints (fill coverage gap)."""
import pytest
from unittest.mock import patch, MagicMock

from app.models.notification import Notification
from app.models.push_subscription import PushSubscription


class TestNotificationList:
    """Test notification listing."""

    def test_list_notifications_returns_user_only(self, client, create_user, db_session):
        """User should only see their own notifications."""
        user1 = create_user(username="notif_list1", email="notif_list1@test.com")
        user2 = create_user(username="notif_list2", email="notif_list2@test.com")

        db_session.add(Notification(user_id=user1.id, type="review", message="For user 1"))
        db_session.add(Notification(user_id=user2.id, type="review", message="For user 2"))
        db_session.commit()

        from app.auth import create_token
        token = create_token(user1.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/notifications", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["message"] == "For user 1"

    def test_list_notifications_requires_auth(self, client):
        """Unauthenticated user cannot list notifications."""
        resp = client.get("/api/notifications")
        assert resp.status_code == 401


class TestNotificationMarkRead:
    """Test marking notifications as read."""

    def test_mark_as_read(self, client, create_user, db_session):
        """User can mark their notification as read."""
        user = create_user(username="mark_read", email="mark_read@test.com")
        notif = Notification(user_id=user.id, type="review", message="Read me", is_read=False)
        db_session.add(notif)
        db_session.commit()
        db_session.refresh(notif)

        from app.auth import create_token
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.put(f"/api/notifications/{notif.id}/read", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Marcada como leída"

    def test_mark_as_read_not_found(self, client, create_user):
        """Marking non-existent notification returns 404."""
        user = create_user(username="mark_notfound", email="mark_notfound@test.com")
        from app.auth import create_token
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.put("/api/notifications/999999/read", headers=headers)
        assert resp.status_code == 404

    def test_cannot_mark_others_notification(self, client, create_user, db_session):
        """User cannot mark another user's notification as read."""
        user1 = create_user(username="victim_mark", email="victim_mark@test.com")
        user2 = create_user(username="attacker_mark", email="attacker_mark@test.com")

        notif = Notification(user_id=user1.id, type="review", message="Secret", is_read=False)
        db_session.add(notif)
        db_session.commit()

        from app.auth import create_token
        token = create_token(user2.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.put(f"/api/notifications/{notif.id}/read", headers=headers)
        assert resp.status_code == 404


class TestNotificationMarkAllRead:
    """Test marking all notifications as read."""

    def test_mark_all_as_read(self, client, create_user, db_session):
        """User can mark all notifications as read."""
        user = create_user(username="mark_all", email="mark_all@test.com")
        db_session.add(Notification(user_id=user.id, type="review", message="N1", is_read=False))
        db_session.add(Notification(user_id=user.id, type="review", message="N2", is_read=False))
        db_session.add(Notification(user_id=user.id, type="review", message="N3", is_read=True))
        db_session.commit()

        from app.auth import create_token
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.put("/api/notifications/read-all", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Todas marcadas como leídas"

        # Verify all are read
        notifs = db_session.query(Notification).filter(Notification.user_id == user.id).all()
        assert all(n.is_read for n in notifs)


class TestVapidPublicKey:
    """Test VAPID public key endpoint."""

    def test_vapid_key_not_configured(self, client):
        """When VAPID key is not set, returns 503."""
        with patch("app.routes.notifications.VAPID_PUBLIC_KEY", ""):
            resp = client.get("/api/notifications/vapid-public-key")
            assert resp.status_code == 503


class TestPushSubscribe:
    """Test push subscription management."""

    def test_subscribe_new(self, client, create_user, db_session):
        """User can subscribe to push notifications."""
        user = create_user(username="push_sub", email="push_sub@test.com")
        from app.auth import create_token
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post("/api/notifications/subscribe", headers=headers, json={
            "endpoint": "https://fcm.googleapis.com/fcm/send/abc123",
            "keys": {
                "p256dh": "base64p256dhkey",
                "auth": "base64authkey",
            },
        })
        assert resp.status_code == 200
        assert resp.json()["message"] == "Suscripción guardada"

        # Verify in DB
        sub = db_session.query(PushSubscription).filter(
            PushSubscription.user_id == user.id
        ).first()
        assert sub is not None
        assert sub.p256dh == "base64p256dhkey"

    def test_subscribe_update_existing(self, client, create_user, db_session):
        """Subscribing again with same endpoint should update."""
        user = create_user(username="push_upd", email="push_upd@test.com")
        sub = PushSubscription(
            user_id=user.id,
            endpoint="https://fcm.googleapis.com/fcm/send/existing",
            p256dh="old_key",
            auth="old_auth",
        )
        db_session.add(sub)
        db_session.commit()

        from app.auth import create_token
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post("/api/notifications/subscribe", headers=headers, json={
            "endpoint": "https://fcm.googleapis.com/fcm/send/existing",
            "keys": {
                "p256dh": "new_key",
                "auth": "new_auth",
            },
        })
        assert resp.status_code == 200

        db_session.refresh(sub)
        assert sub.p256dh == "new_key"

    def test_subscribe_missing_keys(self, client, create_user):
        """Subscribe without keys should return 400."""
        user = create_user(username="push_miss", email="push_miss@test.com")
        from app.auth import create_token
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post("/api/notifications/subscribe", headers=headers, json={
            "endpoint": "https://example.com/endpoint",
            "keys": {},
        })
        assert resp.status_code == 400

    def test_subscribe_requires_auth(self, client):
        """Unauthenticated user cannot subscribe."""
        resp = client.post("/api/notifications/subscribe", json={
            "endpoint": "https://example.com",
            "keys": {"p256dh": "key", "auth": "auth"},
        })
        assert resp.status_code == 401


class TestPushUnsubscribe:
    """Test push unsubscription."""

    def test_unsubscribe(self, client, create_user, db_session):
        """User can unsubscribe from push notifications."""
        user = create_user(username="push_unsub", email="push_unsub@test.com")
        sub = PushSubscription(
            user_id=user.id,
            endpoint="https://fcm.googleapis.com/fcm/send/to_delete",
            p256dh="key",
            auth="auth",
        )
        db_session.add(sub)
        db_session.commit()

        from app.auth import create_token
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post("/api/notifications/unsubscribe", headers=headers, json={
            "endpoint": "https://fcm.googleapis.com/fcm/send/to_delete",
            "keys": {"p256dh": "key", "auth": "auth"},
        })
        assert resp.status_code == 200
        assert "eliminada" in resp.json()["message"]

    def test_unsubscribe_not_found(self, client, create_user):
        """Unsubscribing from non-existent endpoint should succeed with message."""
        user = create_user(username="push_unsub_nf", email="push_unsub_nf@test.com")
        from app.auth import create_token
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post("/api/notifications/unsubscribe", headers=headers, json={
            "endpoint": "https://nonexistent.com",
            "keys": {"p256dh": "key", "auth": "auth"},
        })
        assert resp.status_code == 200
        assert "No encontrada" in resp.json()["message"]

    def test_unsubscribe_requires_auth(self, client):
        """Unauthenticated user cannot unsubscribe."""
        resp = client.post("/api/notifications/unsubscribe", json={
            "endpoint": "https://example.com",
            "keys": {"p256dh": "key", "auth": "auth"},
        })
        assert resp.status_code == 401


class TestSendPushHelpers:
    """Test internal push sending helpers."""

    def test_send_push_not_configured(self, client):
        """When VAPID not configured, send_push_to_user returns 0."""
        from app.routes.notifications import send_push_to_user
        with patch("app.routes.notifications.VAPID_PRIVATE_KEY", ""):
            result = send_push_to_user(None, 1, "Test", "Body")
            assert result == 0

    def test_send_push_no_subscriptions(self, client, db_session):
        """send_push_to_user returns 0 when no subscriptions exist."""
        from app.routes.notifications import send_push_to_user
        with patch("app.routes.notifications.VAPID_PRIVATE_KEY", "some_key"):
            result = send_push_to_user(db_session, 999, "Test", "Body")
            assert result == 0

    def test_send_push_import_error(self, client, db_session, create_user):
        """send_push_to_user handles ImportError gracefully."""
        from app.routes.notifications import send_push_to_user
        user = create_user(username="push_import", email="push_import@test.com")
        sub = PushSubscription(
            user_id=user.id,
            endpoint="https://example.com/ep",
            p256dh="key",
            auth="auth",
        )
        db_session.add(sub)
        db_session.commit()

        with patch("app.routes.notifications.VAPID_PRIVATE_KEY", "some_key"):
            with patch.dict("sys.modules", {"pywebpush": None}):
                # Force reimport to trigger ImportError
                import importlib
                import app.routes.notifications as notif_module
                original = getattr(notif_module, "webpush", None)
                result = send_push_to_user(db_session, user.id, "Test", "Body")
                # Should return 0 due to import error
                assert result == 0

    def test_send_push_to_all_not_configured(self, client):
        """send_push_to_all returns 0 when not configured."""
        from app.routes.notifications import send_push_to_all
        with patch("app.routes.notifications.VAPID_PRIVATE_KEY", ""):
            result = send_push_to_all(None, "Test", "Body")
            assert result == 0

    def test_send_push_to_all_no_subscriptions(self, client, db_session):
        """send_push_to_all returns 0 when no subscriptions exist."""
        from app.routes.notifications import send_push_to_all
        with patch("app.routes.notifications.VAPID_PRIVATE_KEY", "some_key"):
            result = send_push_to_all(db_session, "Test", "Body")
            assert result == 0
