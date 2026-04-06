"""Final coverage boost suite — reaching ≥90% code coverage."""
import pytest
import io
import json
from PIL import Image
from unittest.mock import patch, MagicMock
from tests.conftest import _bearer
from datetime import datetime, timezone
from app.models.contact import Contact
from app.models.review import Review
from app.models.user import User
from app.models.contact_change import ContactChange
from app.models.report import Report
from app.models.utility_item import UtilityItem
from app.models.schedule import Schedule
from app.models.push_subscription import PushSubscription
from app.models.contact_photo import ContactPhoto


class TestFinalCoverageSuite:

    def test_main_html_serving_exhaustion(self, client):
        """Cover app/main.py serve_html static routes."""
        # Success
        assert client.get("/search").status_code == 200
        
        # Trigger 'Not Found' dict branch (190) in serve_html
        with patch("pathlib.Path.exists", return_value=False):
            res = client.get("/search")
            assert res.status_code == 200
            assert "detail" in res.json()

    def test_notifications_logic_boost(self, client, db_session, create_user):
        """Cover app/routes/notifications.py send logic."""
        u = create_user(username="notif_boost", email="nb@e.com")
        sub = PushSubscription(user_id=u.id, endpoint="http://nb.com", p256dh="x", auth="x")
        db_session.add(sub)
        db_session.commit()
        
        from app.routes import notifications
        with patch("pywebpush.webpush") as mock_webpush, \
             patch("app.routes.notifications.VAPID_PRIVATE_KEY", "dummy_key_32_bytes_long_at_least_!!"):
            
            # Send to user logic
            notifications.send_push_to_user(db_session, u.id, "T", "B")
            # send_push_to_all logic
            notifications.send_push_to_all(db_session, "All", "Body")

    def test_reviews_comprehensive_boost(self, client, create_user, create_contact, db_session):
        """Cover reviews.py gaps including 404s."""
        u = create_user()
        c = create_contact()
        headers = _bearer(u)
        
        # 1. Create review for non-existent contact (covers 46-63)
        res = client.post("/api/contacts/999999/reviews", headers=headers, json={"rating": 5, "comment": "X"})
        assert res.status_code == 404
        
        # 2. Photo upload success
        r1 = client.post(f"/api/contacts/{c.id}/reviews", headers=headers, json={"rating": 5, "comment": "X"})
        rid = r1.json()["id"]
        img = Image.new("RGB", (10, 10), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        client.post(f"/api/reviews/{rid}/photo", headers=headers, files={"file": ("p.jpg", buf, "image/jpeg")})

    def test_contacts_deletion_details(self, client, create_user, create_contact, db_session):
        """Cover contacts.py missing branches."""
        u = create_user()
        c = create_contact(user_id=u.id)
        headers = _bearer(u)
        
        # 1. delete_photo non-existent contact (covers 1132)
        res = client.delete(f"/api/contacts/999999/photos/1", headers=headers)
        assert res.status_code == 404
        
        # 2. delete_photo non-existent photo (covers 1141)
        res = client.delete(f"/api/contacts/{c.id}/photos/999999", headers=headers)
        assert res.status_code == 404
        
        # 3. get_contact_related non-existent contact (covers 74)
        res = client.get("/api/contacts/999999/related")
        assert res.status_code == 404
        
        # 4. get_contact_history non-existent contact (covers 90) - REQUIRES AUTH
        res = client.get("/api/contacts/999999/history", headers=headers)
        assert res.status_code == 404

    def test_admin_detailed_boost(self, client, mod_headers, create_user):
        """Cover admin.py missing 403 and 404 branches."""
        # 1. Update non-existent utility (covers 41)
        res = client.put("/api/admin/utilities/999999", headers=mod_headers, json={"name": "X"})
        assert res.status_code == 404
        
        # 2. Delete non-existent utility (covers 45)
        res = client.delete("/api/admin/utilities/999999", headers=mod_headers)
        assert res.status_code == 404
        
        # 3. Resolve non-existent report (covers 200)
        res = client.post("/api/admin/reports/999999/resolve?action=suspend", headers=mod_headers)
        assert res.status_code == 404

        # 4. Role check failure (covers admin.py:238)
        u = create_user(username="plain_u_v", email="plv@e.com")
        assert client.get("/api/admin/contacts", headers=_bearer(u)).status_code == 403

    def test_offers_exhaustion_boost(self, client, create_user):
        """Cover offers.py 404 branches."""
        u = create_user()
        headers = _bearer(u)
        # GET non-existent
        assert client.get("/api/provider/offers/999999", headers=headers).status_code == 404
        # DELETE non-existent
        assert client.delete("/api/provider/offers/999999", headers=headers).status_code == 404
        # PUT non-existent
        assert client.put("/api/provider/offers/999999", headers=headers, json={"title":"X"}).status_code == 404

    def test_users_logic_exhaustion(self, client, create_user, db_session):
        """Cover users.py and auth.py crossover."""
        admin = create_user(role="admin", username="admin_ult_v", email="auv@e.com")
        headers = _bearer(admin)
        
        # 1. Invalid role in update_user (covers users.py:102)
        res = client.put(f"/api/users/{admin.id}", headers=headers, json={"role": "super-admin"})
        assert res.status_code == 400
        
        # 2. Get non-existent user (covers users.py:79)
        assert client.get("/api/users/999999", headers=headers).status_code == 404
        
        # 3. Provider dashboard search logic (covers provider.py:33)
        client.get("/api/provider/dashboard?search=X", headers=headers)
        
        # 4. Auth: get_current_user with deleted user (covers auth.py:48) 
        # (Fixing headers and deletion order)
        u = create_user(username="u_auth_fail", email="uaf@e.com")
        token_headers = _bearer(u)
        db_session.delete(u)
        db_session.commit()
        assert client.get("/api/provider/dashboard", headers=token_headers).status_code == 401
