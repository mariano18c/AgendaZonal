import pytest
from tests.conftest import _bearer
from app.models.push_subscription import PushSubscription
from app.models.utility_item import UtilityItem
from unittest.mock import patch

class TestEmergencyMode:
    def test_subscribe_with_geo(self, client, create_user, db_session):
        user = create_user()
        r = client.post("/api/notifications/subscribe", headers=_bearer(user),
                          json={
                              "endpoint": "https://fcm.googleapis.com/fcm/send/emergency-test",
                              "keys": {"p256dh": "test_p256dh", "auth": "test_auth"},
                              "latitude": -32.9,
                              "longitude": -60.6,
                              "city": "Rosario"
                          })
        assert r.status_code in (200, 201)
        
        # Verify in DB
        sub = db_session.query(PushSubscription).filter_by(user_id=user.id).first()
        assert sub.city == "Rosario"
        assert sub.latitude == -32.9

    def test_create_priority_utility_triggers_push(self, client, create_user, db_session):
        admin = create_user(role="admin")
        
        # Mock send_push_to_zone to avoid real webpush calls
        with patch("app.routes.admin.send_push_to_zone") as mock_push:
            payload = {
                "type": "emergencia",
                "name": "Incendio Forestal",
                "city": "Rosario",
                "is_priority": True,
                "notification_message": "Evacuar zona norte"
            }
            r = client.post("/api/admin/utilities", headers=_bearer(admin), json=payload)
            assert r.status_code in (200, 201)
            
            # Verify priority flag in DB
            item = db_session.query(UtilityItem).filter_by(name="Incendio Forestal").first()
            assert item.is_priority is True
            
            # Verify push was triggered
            mock_push.assert_called_once()
            args, kwargs = mock_push.call_args
            assert kwargs["city"] == "Rosario"
            assert "Evacuar zona norte" in kwargs["body"]
            assert "Incendio Forestal" in kwargs["title"]

    def test_create_normal_utility_no_push(self, client, create_user):
        admin = create_user(role="admin")
        with patch("app.routes.admin.send_push_to_zone") as mock_push:
            payload = {
                "type": "otro",
                "name": "Farmacia Turno Normal",
                "city": "Rosario",
                "is_priority": False
            }
            client.post("/api/admin/utilities", headers=_bearer(admin), json=payload)
            mock_push.assert_not_called()
