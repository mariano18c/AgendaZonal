"""Integration tests for notifications endpoints."""
import pytest
from app.models.notification import Notification


class TestListNotifications:
    """GET /api/notifications"""

    def test_returns_empty_list_for_new_user(self, client, auth_headers):
        headers = auth_headers()
        resp = client.get("/api/notifications", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_requires_auth(self, client):
        resp = client.get("/api/notifications")
        assert resp.status_code == 401

    def test_returns_own_notifications(self, client, create_user, database_session):
        user = create_user()
        notif = Notification(user_id=user.id, type="review", message="Hello")
        database_session.add(notif)
        database_session.commit()

        resp = client.post("/api/auth/login", json={
            "username_or_email": "testuser",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = client.get("/api/notifications", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["message"] == "Hello"

    def test_returns_only_own_notifications(self, client, create_user, database_session):
        """Notifications from other users should not appear."""
        user1 = create_user(username="user1", email="user1@test.com")
        user2 = create_user(username="user2", email="user2@test.com")

        database_session.add(Notification(user_id=user2.id, type="review", message="Private"))
        database_session.commit()

        resp = client.post("/api/auth/login", json={
            "username_or_email": "user1",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = client.get("/api/notifications", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestMarkNotificationAsRead:
    """PUT /api/notifications/{id}/read"""

    def test_mark_as_read(self, client, create_user, database_session):
        user = create_user()
        notif = Notification(user_id=user.id, type="review", message="Hello")
        database_session.add(notif)
        database_session.commit()
        database_session.refresh(notif)

        resp = client.post("/api/auth/login", json={
            "username_or_email": "testuser",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = client.put(f"/api/notifications/{notif.id}/read", headers=headers)
        assert resp.status_code == 200

        database_session.refresh(notif)
        assert notif.is_read is True

    def test_cannot_mark_other_users_notification(self, client, create_user, database_session):
        user1 = create_user(username="user1", email="user1@test.com")
        user2 = create_user(username="user2", email="user2@test.com")

        notif = Notification(user_id=user2.id, type="review", message="Secret")
        database_session.add(notif)
        database_session.commit()
        database_session.refresh(notif)

        resp = client.post("/api/auth/login", json={
            "username_or_email": "user1",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = client.put(f"/api/notifications/{notif.id}/read", headers=headers)
        assert resp.status_code == 404

    def test_nonexistent_notification(self, client, auth_headers):
        headers = auth_headers()
        resp = client.put("/api/notifications/99999/read", headers=headers)
        assert resp.status_code == 404

    def test_requires_auth(self, client):
        resp = client.put("/api/notifications/1/read")
        assert resp.status_code == 401


class TestMarkAllAsRead:
    """PUT /api/notifications/read-all"""

    def test_marks_all_own_notifications(self, client, create_user, database_session):
        user = create_user()

        for i in range(3):
            database_session.add(Notification(
                user_id=user.id, type="review", message=f"Message {i}"
            ))
        database_session.commit()

        resp = client.post("/api/auth/login", json={
            "username_or_email": "testuser",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = client.put("/api/notifications/read-all", headers=headers)
        assert resp.status_code == 200

        notifs = database_session.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False
        ).all()
        assert len(notifs) == 0

    def test_does_not_affect_other_users(self, client, create_user, database_session):
        user1 = create_user(username="user1", email="user1@test.com")
        user2 = create_user(username="user2", email="user2@test.com")

        database_session.add(Notification(user_id=user2.id, type="review", message="Msg"))
        database_session.commit()

        resp = client.post("/api/auth/login", json={
            "username_or_email": "user1",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        client.put("/api/notifications/read-all", headers=headers)

        notif = database_session.query(Notification).filter(
            Notification.user_id == user2.id
        ).first()
        assert notif.is_read is False

    def test_requires_auth(self, client):
        resp = client.put("/api/notifications/read-all")
        assert resp.status_code == 401
