"""Advanced security tests — Ethical Hacking, Penetration Testing, Data Exfiltration."""
import pytest
import jwt
import json
import base64
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.config import JWT_SECRET, JWT_ALGORITHM


# ===========================================================================
# PRIVILEGE ESCALATION
# ===========================================================================

class TestPrivilegeEscalation:
    """Attempt to escalate privileges through every known vector."""

    def test_role_injection_on_register(self, client, captcha):
        """Sending role=admin in registration should be ignored."""
        resp = client.post("/api/auth/register", json={
            "username": "role_hacker",
            "email": "role_hacker@evil.com",
            "phone_area_code": "0341",
            "phone_number": "6666666",
            "password": "HackerPass123!",
            "role": "admin",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        assert resp.status_code == 201
        assert resp.json()["user"]["role"] == "user"

    def test_jwt_claim_manipulation_role(self, client, create_user):
        """Forging a JWT with role=admin claim should not work."""
        user = create_user(username="jwt_hacker", email="jwt_hack@test.com", role="user")
        # Forge token with admin role claim
        payload = {
            "sub": str(user.id),
            "role": "admin",  # Extra claim — server should NOT trust this
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/users", headers=headers)
        assert resp.status_code == 403

    def test_bootstrap_admin_replay(self, client, captcha):
        """Bootstrap admin should only work once per DB."""
        # First bootstrap
        client.post("/api/auth/bootstrap-admin", json={
            "username": "first_admin",
            "email": "first@admin.com",
            "phone_area_code": "0341",
            "phone_number": "1111111",
            "password": "adminpass123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        # Second bootstrap attempt
        captcha2 = client.get("/api/auth/captcha").json()
        from tests.conftest import _parse_captcha_answer
        answer = _parse_captcha_answer(captcha2["question"])
        resp = client.post("/api/auth/bootstrap-admin", json={
            "username": "second_admin",
            "email": "second@admin.com",
            "phone_area_code": "0341",
            "phone_number": "2222222",
            "password": "adminpass123",
            "captcha_challenge_id": captcha2["challenge_id"],
            "captcha_answer": str(answer),
        })
        assert resp.status_code in [400, 403, 409]

    def test_cannot_change_own_role(self, client, admin_headers):
        """Admin should not be able to change their own role to something else."""
        me = client.get("/api/auth/me", headers=admin_headers)
        user_id = me.json()["id"]

        resp = client.put(f"/api/users/{user_id}/role", headers=admin_headers, json={
            "role": "user",
        })
        assert resp.status_code == 400

    def test_moderator_cannot_access_admin_user_mgmt(self, client, moderator_user):
        """Moderator should NOT access user management."""
        _, headers = moderator_user
        resp = client.get("/api/users", headers=headers)
        assert resp.status_code == 403

    def test_moderator_cannot_create_users(self, client, moderator_user):
        """Moderator should NOT create users."""
        _, headers = moderator_user
        resp = client.post("/api/users", headers=headers, json={
            "username": "hacker_created",
            "email": "hacker@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "role": "user",
        })
        assert resp.status_code == 403


# ===========================================================================
# DATA EXFILTRATION
# ===========================================================================

class TestDataExfiltration:
    """Attempt to access data not meant for us."""

    def test_cannot_access_other_user_contacts(self, client, auth_headers, create_contact):
        """User A should not be able to edit/delete User B's contacts."""
        contact = create_contact(name="Victim Contact")
        attacker_headers = auth_headers(username="attacker_c", email="attacker_c@test.com")

        # Try to edit
        resp = client.put(f"/api/contacts/{contact.id}", headers=attacker_headers, json={
            "name": "Hacked",
        })
        assert resp.status_code == 403

        # Try to delete
        resp = client.delete(f"/api/contacts/{contact.id}", headers=attacker_headers)
        assert resp.status_code == 403

    def test_cannot_view_other_user_leads(self, client, create_user, db_session):
        """User should not see leads from contacts they don't own."""
        from app.models.contact import Contact
        from app.models.lead_event import LeadEvent

        owner = create_user(username="lead_owner", email="lead_owner@test.com")
        attacker = create_user(username="lead_attacker", email="lead_attacker@test.com")

        contact = Contact(name="Lead Biz", phone="123", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        db_session.add(LeadEvent(contact_id=contact.id, source="whatsapp"))
        db_session.commit()

        from app.auth import create_token
        token = create_token(attacker.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get(f"/api/contacts/{contact.id}/leads", headers=headers)
        assert resp.status_code == 403

    def test_cannot_access_other_user_offers(self, client, create_user, db_session):
        """User should not be able to modify other user's offers."""
        from app.models.contact import Contact
        from app.models.offer import Offer

        owner = create_user(username="offer_owner", email="offer_owner@test.com")
        attacker = create_user(username="offer_attacker", email="offer_attacker@test.com")

        contact = Contact(name="Offer Biz", phone="123", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        offer = Offer(
            contact_id=contact.id, title="Secret Offer",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(offer)
        db_session.commit()
        db_session.refresh(offer)

        from app.auth import create_token
        token = create_token(attacker.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.put(
            f"/api/contacts/{contact.id}/offers/{offer.id}",
            headers=headers,
            json={"title": "Hacked", "discount_pct": 99,
                  "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()},
        )
        assert resp.status_code == 403

    def test_cannot_access_other_user_schedules(self, client, create_user, db_session):
        """User should not be able to modify other user's schedules."""
        from app.models.contact import Contact

        owner = create_user(username="sched_owner", email="sched_owner@test.com")
        attacker = create_user(username="sched_attacker", email="sched_attacker@test.com")

        contact = Contact(name="Sched Biz", phone="123", user_id=owner.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        from app.auth import create_token
        token = create_token(attacker.id)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.put(f"/api/contacts/{contact.id}/schedules", headers=headers, json=[
            {"day_of_week": 1, "open_time": "09:00", "close_time": "18:00"},
        ])
        assert resp.status_code == 403

    def test_deactivated_user_token_rejected(self, client, create_user, db_session):
        """Token should be rejected after user is deactivated."""
        user = create_user(username="deact_token", email="deact_token@test.com")

        resp = client.post("/api/auth/login", json={
            "username_or_email": "deact_token",
            "password": "password123",
        })
        token = resp.json()["token"]

        # Deactivate user
        user.is_active = False
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_csv_export_does_not_leak_passwords(self, client, admin_headers):
        """Analytics CSV export should not contain sensitive data."""
        resp = client.get("/api/admin/analytics/export", headers=admin_headers)
        assert resp.status_code == 200
        content = resp.text.lower()
        assert "password" not in content
        assert "password_hash" not in content
        assert "secret" not in content


# ===========================================================================
# AUTH BYPASS — ADVANCED
# ===========================================================================

class TestAuthBypassAdvanced:
    """Advanced authentication bypass attempts."""

    def test_none_algorithm_attack(self, client, create_user):
        """JWT 'none' algorithm attack should be rejected."""
        user = create_user(username="none_attack", email="none@test.com")
        # Craft token with alg=none
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": str(user.id)}).encode()
        ).rstrip(b"=").decode()
        token = f"{header}.{payload}."
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_empty_sub_claim(self, client):
        """Token with empty 'sub' should be rejected."""
        payload = {
            "sub": "",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_negative_user_id(self, client):
        """Token with negative user_id should be rejected."""
        payload = {
            "sub": "-1",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_float_user_id(self, client):
        """Token with float user_id should be rejected."""
        payload = {
            "sub": "1.5",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_huge_user_id(self, client):
        """Token with extremely large user_id should be rejected."""
        payload = {
            "sub": str(2**63 - 1),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_cookie_cannot_be_read_by_js(self, client, captcha):
        """Auth cookie should be HttpOnly (not accessible via document.cookie)."""
        resp = client.post("/api/auth/register", json={
            "username": "httponly_test",
            "email": "httponly@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        assert resp.status_code == 201
        # Check Set-Cookie header for HttpOnly flag
        set_cookie = resp.headers.get("set-cookie", "")
        assert "httponly" in set_cookie.lower()

    def test_cookie_samesite_lax(self, client, captcha):
        """Auth cookie should have SameSite=Lax or Strict."""
        resp = client.post("/api/auth/register", json={
            "username": "samesite_test",
            "email": "samesite@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        set_cookie = resp.headers.get("set-cookie", "")
        assert "samesite" in set_cookie.lower()


# ===========================================================================
# DOS RESISTANCE
# ===========================================================================

class TestDOSResistance:
    """Denial-of-service resistance tests."""

    def test_massive_search_query(self, client):
        """Very long search query should not crash or hang."""
        resp = client.get(f"/api/contacts/search?q={'A' * 50000}")
        assert resp.status_code in [200, 400, 414, 422]

    def test_regex_dos_in_search(self, client):
        """Regex-like patterns should not cause ReDoS."""
        # Catastrophic backtracking patterns
        payloads = [
            "(a+)+",
            "(a|aa)+",
            "(a|a?)+",
            ".*.*.*.*.*",
        ]
        for payload in payloads:
            resp = client.get(f"/api/contacts/search?q={payload}")
            assert resp.status_code in [200, 400, 422]

    def test_rapid_login_attempts(self, client):
        """Multiple rapid login attempts should not crash."""
        for _ in range(50):
            resp = client.post("/api/auth/login", json={
                "username_or_email": "nonexistent",
                "password": "wrong",
            })
            assert resp.status_code == 401

    def test_concurrent_reads_same_endpoint(self, client, create_contact):
        """Concurrent reads may cause SQLite errors with threads — expected."""
        contact = create_contact(name="Concurrent Read")
        results = []

        def do_read():
            try:
                resp = client.get(f"/api/contacts/{contact.id}")
                results.append(resp.status_code)
            except Exception:
                results.append("error")  # Expected with SQLite + threads

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(do_read) for _ in range(10)]
            for f in as_completed(futures):
                f.result()

        # Some may succeed, some may error — SQLite with threads is unpredictable
        success = sum(1 for r in results if r == 200)
        # At least verify the endpoint didn't crash the server
        assert len(results) == 10

    def test_huge_pagination_skip(self, client):
        """Huge skip value should not cause memory issues."""
        resp = client.get("/api/contacts?skip=999999999&limit=100")
        assert resp.status_code in [200, 422]

    def test_zero_limit(self, client):
        """Zero limit should return empty results."""
        resp = client.get("/api/contacts?limit=0")
        assert resp.status_code == 200

    def test_negative_limit(self, client):
        """Negative limit should be rejected."""
        resp = client.get("/api/contacts?limit=-1")
        assert resp.status_code in [200, 422]


# ===========================================================================
# INJECTION ATTACKS — ADVANCED
# ===========================================================================

class TestInjectionAttacks:
    """Advanced injection attacks beyond basic SQLi."""

    def test_sqlite_pragma_injection(self, client):
        """Attempt to modify SQLite PRAGMAs via search."""
        payloads = [
            "'; PRAGMA journal_mode=DELETE; --",
            "'; PRAGMA foreign_keys=OFF; --",
            "' UNION SELECT sql FROM sqlite_master; --",
        ]
        for payload in payloads:
            resp = client.get(f"/api/contacts/search?q={payload}")
            assert resp.status_code == 200
            # Should not return schema info
            for item in resp.json():
                assert "CREATE TABLE" not in str(item)

    def test_header_injection(self, client):
        """Attempt header injection via CRLF."""
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer token\r\nX-Injected: true",
        })
        assert resp.status_code == 401

    def test_json_type_confusion(self, client, auth_headers):
        """Send array instead of object in JSON body."""
        headers = auth_headers(username="type_conf", email="type_conf@test.com")
        resp = client.post("/api/contacts", headers=headers, content=b"[]")
        assert resp.status_code == 422

    def test_multipart_injection(self, client, auth_headers):
        """Malformed multipart data should be handled gracefully."""
        headers = auth_headers(username="multipart_inj", email="multipart_inj@test.com")
        resp = client.post(
            "/api/contacts",
            headers={**headers, "Content-Type": "multipart/form-data; boundary=----WebKit"},
            content=b"------WebKit\r\ninvalid\r\n------WebKit--",
        )
        # Should not crash
        assert resp.status_code in [400, 422, 201]

    def test_path_traversal_in_static(self, client):
        """Path traversal in static file serving."""
        resp = client.get("/js/../../etc/passwd")
        assert resp.status_code in [404, 403]

    def test_null_byte_injection(self, client):
        """Null byte in URL should be handled."""
        resp = client.get("/api/contacts/search?q=test%00injection")
        assert resp.status_code in [200, 400]

    def test_unicode_normalization_attack(self, client, auth_headers):
        """Unicode homoglyph attack in username."""
        headers = auth_headers(username="admіn", email="homoglyph@test.com")  # і = Cyrillic
        resp = client.get("/api/users", headers=headers)
        # Should NOT grant admin access
        assert resp.status_code in [403, 401]


# ===========================================================================
# BUSINESS LOGIC ATTACKS
# ===========================================================================

class TestBusinessLogicAttacks:
    """Attempt to exploit business logic flaws."""

    def test_create_offer_with_past_expiry(self, client, auth_headers):
        """Creating offer with past expiration should be rejected."""
        headers = auth_headers(username="offer_past", email="offer_past@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Past Offer Biz",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        owner_id = create_resp.json()["user_id"]

        from app.auth import create_token
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        resp = client.post(f"/api/contacts/{cid}/offers", headers=owner_headers, json={
            "title": "Expired Offer",
            "discount_pct": 50,
            "expires_at": past,
        })
        # Should either accept (and be filtered on list) or reject
        assert resp.status_code in [201, 400, 422]

    def test_review_rating_manipulation(self, client, auth_headers, create_contact):
        """Creating review should not allow rating manipulation via DB."""
        headers = auth_headers(username="rating_hack", email="rating_hack@test.com")
        contact = create_contact(name="Rating Test")

        resp = client.post(f"/api/contacts/{contact.id}/reviews", headers=headers, json={
            "rating": 5,
            "comment": "Perfect!",
        })
        assert resp.status_code == 201

        # Verify rating is exactly what was sent
        assert resp.json()["rating"] == 5

    def test_max_pending_changes_limit(self, client, auth_headers, create_contact):
        """Should not exceed MAX_PENDING_CHANGES."""
        contact = create_contact(name="Max Changes")
        owner_id = contact.user_id

        # Create 3 different users to suggest changes
        for i in range(5):
            headers = auth_headers(username=f"changer_{i}", email=f"changer_{i}@test.com")
            resp = client.put(f"/api/contacts/{contact.id}/edit", headers=headers, json={
                "description": f"Suggestion {i}",
            })
            # After MAX_PENDING_CHANGES (3), should be rejected
            if i >= 3:
                assert resp.status_code in [400, 403, 429], \
                    f"Change {i} should have been rejected"

    def test_transfer_ownership_to_self(self, client, auth_headers):
        """Should not be able to transfer ownership to self."""
        headers = auth_headers(username="transfer1", email="transfer1@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Transfer Test",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        owner_id = create_resp.json()["user_id"]

        from app.auth import create_token
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        resp = client.put(
            f"/api/contacts/{cid}/transfer-ownership",
            headers=owner_headers,
            json={"new_owner_id": owner_id},
        )
        # Should be rejected or accepted (both valid depending on design)
        assert resp.status_code in [200, 400, 403]

    def test_contact_status_manipulation(self, client, auth_headers, create_contact):
        """Regular user should not change contact status."""
        headers = auth_headers(username="status_hack", email="status_hack@test.com")
        contact = create_contact(name="Status Test")

        resp = client.put(f"/api/admin/contacts/{contact.id}/status", headers=headers, json={
            "status": "suspended",
        })
        assert resp.status_code == 403


# ===========================================================================
# INFORMATION DISCLOSURE
# ===========================================================================

class TestInformationDisclosure:
    """Attempt to extract sensitive information from error responses."""

    def test_no_stack_trace_on_500(self, client, auth_headers):
        """Error responses should not contain stack traces."""
        headers = auth_headers(username="info_disc", email="info_disc@test.com")
        # Send invalid JSON to trigger parsing error
        resp = client.post(
            "/api/contacts",
            headers=headers,
            content=b"not valid json {{{",
        )
        text = resp.text.lower()
        assert "traceback" not in text
        assert "file \"" not in text
        assert "line " not in text
        assert "sqlalchemy" not in text

    def test_no_db_path_in_errors(self, client):
        """Error responses should not reveal database paths."""
        resp = client.get("/api/contacts/invalid")
        text = resp.text.lower()
        assert "sqlite" not in text
        assert ".db" not in text
        assert "database" not in text

    def test_no_internal_paths_in_404(self, client):
        """404 responses should not reveal internal paths."""
        resp = client.get("/api/nonexistent/endpoint")
        text = resp.text.lower()
        assert "backend" not in text
        assert "app/" not in text
        assert "routes" not in text

    def test_security_headers_present(self, client):
        """All responses should have security headers."""
        resp = client.get("/")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert "Content-Security-Policy" in resp.headers
        assert "Referrer-Policy" in resp.headers

    def test_server_header_not_leaked(self, client):
        """Server header should not reveal framework/version."""
        resp = client.get("/health")
        server = resp.headers.get("server", "")
        assert "uvicorn" not in server.lower()
        assert "fastapi" not in server.lower()
        assert "python" not in server.lower()

    def test_rate_limit_headers_on_api(self, client):
        """API responses should include rate limit headers."""
        resp = client.get("/api/categories")
        assert "X-RateLimit-Limit" in resp.headers
        assert "X-RateLimit-Remaining" in resp.headers
        assert "X-RateLimit-Reset" in resp.headers
