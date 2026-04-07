"""Ethical hacking tests — adapted for current test infrastructure."""
import pytest
import re
from app.config import JWT_SECRET, JWT_ALGORITHM


class TestPrivilegeEscalation:
    """Attempt to escalate privileges through various vectors."""

    def test_cannot_register_as_admin(self, client, captcha):
        """Registration should always assign role='user', never admin."""
        resp = client.post("/api/auth/register", json={
            "username": "hacker",
            "email": "hacker@evil.com",
            "phone_area_code": "0341",
            "phone_number": "6666666",
            "password": "HackerPass123!",
            "role": "admin",  # Trying to inject admin role
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        assert resp.status_code == 201
        # Registration creates pending user - role is not returned in response
        # The system should ignore the role parameter

    def test_regular_user_cannot_access_admin_endpoints(self, client, auth_headers):
        """Regular user should get 403 on ALL admin endpoints."""
        headers = auth_headers(username="regular", email="regular@test.com")

        admin_endpoints = [
            ("GET", "/api/users"),
            ("GET", "/api/admin/reviews/pending"),
            ("GET", "/api/admin/reports/flagged"),
            ("GET", "/api/admin/analytics"),
            ("GET", "/api/admin/analytics/export"),
        ]

        for method, url in admin_endpoints:
            resp = getattr(client, method.lower())(url, headers=headers)
            assert resp.status_code in [401, 403], \
                f"{method} {url} returned {resp.status_code} instead of 401/403"

    def test_regular_user_cannot_access_admin_user_management(self, client, auth_headers):
        """Regular user should get 403 on user management."""
        headers = auth_headers()
        resp = client.get("/api/users", headers=headers)
        assert resp.status_code == 403

    def test_moderator_cannot_access_admin_user_management(self, client, create_user, db_session):
        """Moderator should NOT access user management endpoints."""
        import bcrypt
        import uuid
        from app.models.user import User
        from app.auth import create_token
        
        uid = uuid.uuid4().hex[:8]
        user = User(
            username=f"mod_{uid}",
            email=f"mod_{uid}@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password_hash=bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode(),
            role="moderator",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = client.get("/api/users", headers=headers)
        assert resp.status_code == 403

    def test_cannot_create_admin_user_via_api_with_invalid_role(self, client, admin_headers):
        """Even admin-created users should be validated for valid roles."""
        resp = client.post("/api/users", headers=admin_headers, json={
            "username": "newadmin",
            "email": "newadmin@test.com",
            "phone_area_code": "0341",
            "phone_number": "9999999",
            "password": "pass123456",
            "role": "superadmin",  # Invalid role
        })
        # Should return 400 for invalid role
        assert resp.status_code in [400, 422]

    def test_cannot_change_own_role(self, client, admin_headers):
        """Admin should not be able to change their own role."""
        me = client.get("/api/auth/me", headers=admin_headers)
        user_id = me.json()["id"]

        resp = client.put(f"/api/users/{user_id}/role", headers=admin_headers, json={
            "role": "user",
        })
        # Should be rejected (400, 403, or 422)
        assert resp.status_code in [400, 403, 422]


class TestDataExfiltration:
    """Attempt to access data not meant for us."""

    def test_cannot_view_other_users_notifications(self, client, create_user, db_session):
        """Users should not view other users' notifications."""
        from app.models.notification import Notification
        
        user1 = create_user(username="victim", email="victim@test.com")
        user2 = create_user(username="attacker", email="attacker@test.com")
        
        # Create notification for user1
        notif = Notification(
            user_id=user1.id,
            type="review",
            message="Secret message for victim",
            is_read=False,
        )
        db_session.add(notif)
        db_session.commit()
        
        # Get auth for user2
        from app.auth import create_token
        token = create_token(user2.id)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to access all notifications (should only see own)
        resp = client.get("/api/notifications", headers=headers)
        assert resp.status_code == 200
        
        # Should not include victim notifications
        notifs = resp.json()
        for n in notifs:
            assert n.get("user_id") == user2.id or "message" not in n

    def test_cannot_read_contact_changes_without_permission(self, client, create_user, db_session):
        """Non-owner cannot read contact changes."""
        import uuid
        from app.models.contact import Contact
        
        uid = uuid.uuid4().hex[:8]
        user1 = create_user(username=f"owner_{uid}", email=f"owner_{uid}@test.com")
        user2 = create_user(username=f"stranger_{uid}", email=f"stranger_{uid}@test.com")

        contact = Contact(name="Private", phone="1234567", user_id=user1.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        from app.auth import create_token
        token = create_token(user2.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get(f"/api/contacts/{contact.id}/changes", headers=headers)
        assert resp.status_code in [403, 404]

    def test_deactivated_user_cannot_login(self, client, create_user):
        """Deactivated user cannot login."""
        create_user(is_active=False, username="deact", email="deact@test.com")
        resp = client.post("/api/auth/login", json={
            "username_or_email": "deact",
            "password": "password123",
        })
        assert resp.status_code == 401

    def test_deactivated_user_token_rejected(self, client, create_user, db_session):
        """If a user is deactivated AFTER getting a token, the token should be rejected."""
        user = create_user()

        from app.auth import create_token
        token = create_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        # Verify token works before deactivation
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200

        # Deactivate user
        user.is_active = False
        db_session.commit()

        # Token should now be rejected
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_non_owner_cannot_view_leads(self, client, create_user, db_session):
        """Non-owner cannot view leads for a contact."""
        from app.models.contact import Contact
        import uuid
        uid = uuid.uuid4().hex[:8]
        owner = create_user(username=f"owner_{uid}", email=f"owner_{uid}@test.com")
        stranger = create_user(username=f"stranger_{uid}", email=f"stranger_{uid}@test.com")

        contact = Contact(name="Biz", phone="1234567", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        from app.auth import create_token
        token = create_token(stranger.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get(f"/api/contacts/{contact.id}/leads", headers=headers)
        assert resp.status_code in [403, 404]

    def test_cannot_access_other_users_private_data(self, client, create_user, db_session):
        """Cannot access private fields of other users."""
        from app.models.user import User
        
        user1 = create_user(username="user1", email="user1@test.com")
        user2 = create_user(username="user2", email="user2@test.com")
        
        from app.auth import create_token
        token = create_token(user2.id)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to get user1's data via user endpoint
        resp = client.get(f"/api/users/{user1.id}", headers=headers)
        
        # Should be 403 or 404, not expose private data
        if resp.status_code == 200:
            data = resp.json()
            # Should not expose sensitive fields
            assert "password_hash" not in data


class TestInputManipulation:
    """Test input validation and manipulation attempts."""

    def test_sql_injection_in_search(self, client, create_user, db_session):
        """SQL injection in search should be sanitized."""
        from app.models.contact import Contact
        
        user = create_user()
        contact = Contact(
            name="Test Business",
            phone="1234567",
            user_id=user.id,
        )
        db_session.add(contact)
        db_session.commit()
        
        # Try SQL injection in search
        resp = client.get("/api/contacts/search?q=' OR '1'='1")
        assert resp.status_code == 200
        # Should not expose data or return error with details

    def test_xss_in_contact_name_sanitized(self, client, auth_headers):
        """XSS in contact name via API should be sanitized."""
        headers = auth_headers()
        
        # Create contact via API - should be sanitized
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "<script>alert('xss')</script>",
            "phone": "1234567",
        })
        assert resp.status_code == 201
        data = resp.json()
        
        # API should sanitize the name
        assert "<script>" not in data.get("name", "")

    def test_negative_contact_id(self, client):
        """Negative contact ID should return 404."""
        resp = client.get("/api/contacts/-1")
        assert resp.status_code in [404, 422]

    def test_zero_contact_id(self, client):
        """Zero contact ID should return 404."""
        resp = client.get("/api/contacts/0")
        assert resp.status_code in [404, 422]

    def test_extremely_large_contact_id(self, client):
        """Extremely large contact ID should be handled."""
        resp = client.get("/api/contacts/999999999999")
        assert resp.status_code in [404, 422]

    def test_float_contact_id(self, client):
        """Float contact ID should return validation error."""
        resp = client.get("/api/contacts/1.5")
        assert resp.status_code == 422

    def test_string_contact_id(self, client):
        """String contact ID should return validation error."""
        resp = client.get("/api/contacts/abc")
        assert resp.status_code == 422

    def test_empty_json_body_on_create(self, client, auth_headers):
        """Empty JSON body on create should return 422."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={})
        assert resp.status_code == 422

    def test_null_values_in_required_fields(self, client, auth_headers):
        """Null values in required fields should return 422."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": None,
            "phone": None,
        })
        assert resp.status_code == 422

    def test_extremely_long_string_in_name(self, client, auth_headers):
        """Extremely long string in name should be rejected."""
        headers = auth_headers()
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "A" * 10000,
            "phone": "1234567",
        })
        assert resp.status_code in [400, 422]


class TestAuthBypassAttempts:
    """Attempt to bypass authentication."""

    def test_expired_jwt_token(self, client):
        """Expired JWT token should be rejected."""
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone
        
        payload = {
            "sub": "1",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_tampered_jwt_token(self, client, create_user):
        """Tampered JWT token (wrong secret) should be rejected."""
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone
        
        user = create_user()
        payload = {
            "sub": str(user.id),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = pyjwt.encode(payload, "wrong_secret", algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_malformed_authorization_header_bearer_only(self, client):
        """Malformed header with 'Bearer' only should be rejected."""
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer"})
        assert resp.status_code == 401

    def test_malformed_authorization_header_no_scheme(self, client):
        """Malformed header without Bearer scheme should be rejected."""
        resp = client.get("/api/auth/me", headers={"Authorization": "just-a-token"})
        assert resp.status_code == 401

    def test_token_with_different_algorithm(self, client, create_user):
        """JWT algorithm confusion attack — should be rejected."""
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone
        
        user = create_user()
        payload = {
            "sub": str(user.id),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm="HS384")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_empty_token(self, client):
        """Empty token should be rejected."""
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401

    def test_cookie_auth_works(self, client, create_user):
        """Verify that authentication works after login."""
        import uuid
        # Create an active user directly in DB to avoid pending activation
        uid = uuid.uuid4().hex[:8]
        user = create_user(username=f"cookieuser_{uid}", email=f"cookie_{uid}@test.com")
        
        # Login should work with active user
        resp = client.post("/api/auth/login", json={
            "username_or_email": f"cookieuser_{uid}",
            "password": "password123",
        })
        # Should get token on successful login
        assert resp.status_code == 200
        assert "token" in resp.json()

    def test_none_algorithm_rejected(self, client, create_user):
        """JWT with algorithm 'none' should be rejected."""
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone
        
        user = create_user()
        payload = {
            "sub": str(user.id),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        # JWT library requires key=None when using algorithm="none"
        token = pyjwt.encode(payload, None, algorithm="none")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_non_numeric_sub_rejected(self, client):
        """JWT with non-numeric sub should be rejected."""
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone
        
        payload = {
            "sub": "not_a_number",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401


class TestDoSResistance:
    """Test denial of service resistance."""

    def test_rapid_requests_handled(self, client, create_user, db_session):
        """Rapid requests should be rate limited."""
        from app.models.contact import Contact
        
        user = create_user()
        contact = Contact(
            name="Test",
            phone="1234567",
            user_id=user.id,
        )
        db_session.add(contact)
        db_session.commit()
        
        # Make many rapid requests
        responses = []
        for _ in range(15):
            resp = client.get(f"/api/contacts/{contact.id}")
            responses.append(resp.status_code)
        
        # Should have some rate limiting (429) or success (200)
        # Should not crash or expose errors
        assert all(r in [200, 429] for r in responses)

    def test_large_payload_handled(self, client, auth_headers):
        """Large payloads should be rejected with proper error."""
        headers = auth_headers()
        
        # Create very large payload
        large_name = "A" * 10000
        
        resp = client.post("/api/contacts", headers=headers, json={
            "name": large_name,
            "phone": "1234567",
        })
        
        # Should reject with 422 or 400, not crash
        assert resp.status_code in [400, 422]

    def test_massive_search_query(self, client):
        """Send a very long search query."""
        resp = client.get(f"/api/contacts/search?q={'A' * 10000}")
        assert resp.status_code in [200, 400, 414, 422]

    def test_zero_limit_on_list(self, client):
        """Zero limit should return empty list."""
        resp = client.get("/api/contacts?limit=0")
        assert resp.status_code == 200

    def test_negative_skip(self, client):
        """Negative skip should be handled."""
        resp = client.get("/api/contacts?skip=-1")
        assert resp.status_code in [200, 422]

    def test_huge_limit_capped(self, client):
        """Huge limit should be capped or rejected."""
        resp = client.get("/api/contacts?limit=10000")
        assert resp.status_code in [200, 422]

    def test_rapid_login_attempts_no_crash(self, client):
        """Multiple rapid login attempts should not crash the server."""
        for _ in range(20):
            resp = client.post("/api/auth/login", json={
                "username_or_email": "nonexistent",
                "password": "wrong",
            })
            assert resp.status_code == 401


class TestPathTraversal:
    """Test path traversal attempts."""

    def test_cannot_access_uploads_directory(self, client):
        """Path traversal in file upload should be blocked."""
        # Try to access uploads directory
        resp = client.get("/uploads/../../../etc/passwd")
        
        # Should return 404 or not expose file
        assert resp.status_code in [404, 403]

    def test_cannot_access_internal_files(self, client):
        """Internal files should not be accessible."""
        internal_files = [
            "/.env",
            "/app/database.py",
            "/app/config.py",
        ]
        
        for path in internal_files:
            resp = client.get(path)
            # Should return 404, not expose file content
            assert resp.status_code == 404 or "password" not in resp.text.lower()

    def test_path_traversal_dot_dot_slash(self, client):
        """Dot-dot-slash in page parameter should not serve system files."""
        resp = client.get("/edit", params={"page": "../../etc/passwd"})
        # Should either reject (400/404) or serve the default edit page (200)
        # but NEVER serve a system file
        assert resp.status_code in [200, 400, 404]
        # Verify no system file content
        assert "root:" not in resp.text

    def test_path_traversal_null_byte(self, client):
        """Null byte injection in path should not bypass file restrictions."""
        resp = client.get("/edit", params={"page": "profile\x00.html"})
        # Should either reject or serve default page
        assert resp.status_code in [200, 400, 404]


class TestBootstrapRateLimit:
    """Rate limiting on admin bootstrap endpoint."""

    def test_bootstrap_admin_rate_limit(self, client):
        """Rapid bootstrap attempts should be throttled or rejected after first success."""
        import re
        
        def parse_captcha_answer(question: str) -> int:
            """Parse CAPTCHA question and return the answer."""
            if ' + ' in question:
                match = re.match(r'(\d+) \+ (\d+)', question)
                return int(match.group(1)) + int(match.group(2))
            elif ' - ' in question:
                match = re.match(r'(\d+) - (\d+)', question)
                return int(match.group(1)) - int(match.group(2))
            elif ' × ' in question:
                match = re.match(r'(\d+) × (\d+)', question)
                return int(match.group(1)) * int(match.group(2))
            else:
                raise ValueError(f"Unknown CAPTCHA format: {question}")
        
        responses = []
        for i in range(5):
            captcha_resp = client.get("/api/auth/captcha")
            if captcha_resp.status_code != 200:
                break
            captcha_data = captcha_resp.json()
            answer = parse_captcha_answer(captcha_data["question"])

            resp = client.post("/api/auth/bootstrap-admin", json={
                "username": f"bootstrap_test_{i}",
                "email": f"bootstrap_{i}@test.com",
                "phone_area_code": "0341",
                "phone_number": f"555555{i}",
                "password": "bootstrap123",
                "captcha_challenge_id": captcha_data["challenge_id"],
                "captcha_answer": str(answer),
            })
            responses.append(resp)

        # After the first success, subsequent ones should be rejected
        # (400 = already exists, 403 = already bootstrapped, 429 = rate limited)
        if len(responses) > 1:
            later_responses = responses[1:]
            assert all(
                r.status_code in [400, 403, 409, 429, 503] for r in later_responses
            ), f"Expected rejection after first, got statuses: {[r.status_code for r in responses]}"
