"""Integration tests — Notifications (push subscribe, list, mark read)."""
import pytest
from tests.conftest import _bearer


class TestVapidPublicKey:
    def test_get_vapid_key(self, client):
        r = client.get("/api/notifications/vapid-public-key")
        assert r.status_code == 200
        assert "public_key" in r.json()


class TestPushSubscription:
    def test_subscribe(self, client, create_user):
        user = create_user()
        r = client.post("/api/notifications/subscribe", headers=_bearer(user),
                          json={
                              "endpoint": "https://fcm.googleapis.com/fcm/send/test",
                              "keys": {"p256dh": "test_p256dh", "auth": "test_auth"},
                          })
        assert r.status_code in (200, 201)

    def test_subscribe_unauthenticated(self, client):
        r = client.post("/api/notifications/subscribe", json={
            "endpoint": "https://test.com",
            "keys": {"p256dh": "x", "auth": "x"},
        })
        assert r.status_code == 401

    def test_unsubscribe(self, client, create_user):
        user = create_user()
        endpoint = "https://fcm.googleapis.com/fcm/send/unsub-test"
        client.post("/api/notifications/subscribe", headers=_bearer(user),
                     json={"endpoint": endpoint,
                           "keys": {"p256dh": "x", "auth": "x"}})
        r = client.post("/api/notifications/unsubscribe", headers=_bearer(user),
                          json={"endpoint": endpoint, "keys": {"p256dh": "x", "auth": "x"}})
        assert r.status_code == 200


class TestNotificationList:
    def test_list_notifications(self, client, create_user, create_notification):
        user = create_user()
        create_notification(user_id=user.id, message="Test")
        r = client.get("/api/notifications", headers=_bearer(user))
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_list_unauthenticated(self, client):
        r = client.get("/api/notifications")
        assert r.status_code == 401

    def test_mark_as_read(self, client, create_user, create_notification):
        user = create_user()
        n = create_notification(user_id=user.id)
        r = client.put(f"/api/notifications/{n.id}/read", headers=_bearer(user))
        assert r.status_code == 200
        assert "message" in r.json()

    def test_mark_all_as_read(self, client, create_user, create_notification):
        user = create_user()
        create_notification(user_id=user.id)
        create_notification(user_id=user.id, message="Second")
        r = client.put("/api/notifications/read-all", headers=_bearer(user))
        assert r.status_code == 200

    def test_cannot_read_others_notification(self, client, create_user, create_notification):
        owner = create_user()
        other = create_user()
        n = create_notification(user_id=owner.id)
        r = client.put(f"/api/notifications/{n.id}/read", headers=_bearer(other))
        assert r.status_code == 404
