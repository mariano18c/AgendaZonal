"""Robustness tests — SQLite contention, JWT edge cases, upload validation, special chars."""
import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO


# ===========================================================================
# SQLITE CONTENTION
# ===========================================================================

class TestSQLiteContention:
    """Test database behavior under concurrent access."""

    def test_concurrent_reads_no_lock(self, client, create_contact):
        """Multiple concurrent reads should not cause SQLite locks."""
        contact = create_contact(name="Concurrent Read Test")
        results = []
        barrier = threading.Barrier(5)

        def do_read():
            barrier.wait(timeout=5)
            resp = client.get(f"/api/contacts/{contact.id}")
            results.append(resp.status_code)

        threads = [threading.Thread(target=do_read) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        success = sum(1 for r in results if r == 200)
        assert success >= 4, f"Only {success}/5 reads succeeded"

    def test_concurrent_writes_serialized(self, client, auth_headers):
        """Concurrent writes should be serialized, not corrupt data."""
        headers = auth_headers(username="concur_write", email="concur_write@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Concurrent Write",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        owner_id = create_resp.json()["user_id"]

        from app.auth import create_token
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        results = []
        barrier = threading.Barrier(3)

        def do_write(value):
            barrier.wait(timeout=5)
            resp = client.put(
                f"/api/contacts/{cid}",
                headers=owner_headers,
                json={"description": f"Value {value}"},
            )
            results.append((value, resp.status_code))

        threads = [threading.Thread(target=do_write, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        # At least some should succeed
        successes = [r for r in results if r[1] == 200]
        assert len(successes) >= 1, f"No writes succeeded: {results}"

        # Final state should be consistent
        final = client.get(f"/api/contacts/{cid}")
        assert final.status_code == 200
        assert "description" in final.json()

    def test_rapid_create_delete_cycle(self, client, auth_headers):
        """Rapid create-delete cycles should not corrupt DB."""
        headers = auth_headers(username="rapid_cycle", email="rapid_cycle@test.com")
        
        for i in range(10):
            create_resp = client.post("/api/contacts", headers=headers, json={
                "name": f"Cycle {i}",
                "phone": "1234567",
            })
            if create_resp.status_code == 201:
                cid = create_resp.json()["id"]
                delete_resp = client.delete(f"/api/contacts/{cid}", headers=headers)
                assert delete_resp.status_code in [200, 404]

    def test_wal_mode_enabled(self, client):
        """WAL mode should be enabled for better concurrency."""
        from app.database import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode"))
            mode = result.scalar()

        assert mode and mode.upper() == "WAL", f"Expected WAL, got {mode}"

    def test_foreign_keys_enforced(self, client, db_session):
        """Foreign key constraints should be enforced."""
        from sqlalchemy import text

        with db_session.bind.connect() as conn:
            result = conn.execute(text("PRAGMA foreign_keys"))
            fk_enabled = result.scalar()

        assert fk_enabled == 1, "Foreign keys should be enabled"


# ===========================================================================
# JWT EDGE CASES
# ===========================================================================

class TestJWTEdgeCases:
    """Test JWT token edge cases."""

    def test_token_just_before_expiry(self, client, create_user, jwt_helpers):
        """Token that expires in 1 second should still work."""
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone
        from app.config import JWT_SECRET, JWT_ALGORITHM

        user = create_user(username="near_expiry", email="near_expiry@test.com")
        token = pyjwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(timezone.utc) + timedelta(seconds=1),
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200

    def test_token_just_after_expiry(self, client, create_user):
        """Token that expired 1 second ago should be rejected."""
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone
        from app.config import JWT_SECRET, JWT_ALGORITHM

        user = create_user(username="just_expired", email="just_expired@test.com")
        token = pyjwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_token_with_extra_claims(self, client, create_user):
        """Token with extra claims should still work."""
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone
        from app.config import JWT_SECRET, JWT_ALGORITHM

        user = create_user(username="extra_claims", email="extra_claims@test.com")
        token = pyjwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "role": "admin",  # Extra claim — should be ignored
                "custom": "data",
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200
        # Should NOT grant admin access
        resp2 = client.get("/api/users", headers=headers)
        assert resp2.status_code == 403

    def test_token_with_iat_in_future(self, client, create_user):
        """Token with issued-at in the future should still work."""
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone
        from app.config import JWT_SECRET, JWT_ALGORITHM

        user = create_user(username="future_iat", email="future_iat@test.com")
        token = pyjwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iat": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200

    def test_base64url_token_variations(self, client):
        """Malformed base64 in token should be rejected."""
        invalid_tokens = [
            "Bearer not.a.token",
            "Bearer !@#$%^&*()",
            "Bearer " + "A" * 500,
            "Bearer ",
        ]
        for token in invalid_tokens:
            resp = client.get("/api/auth/me", headers={"Authorization": token})
            assert resp.status_code == 401


# ===========================================================================
# UPLOAD VALIDATION
# ===========================================================================

class TestUploadValidation:
    """Test file upload validation."""

    def test_reject_non_image_file(self, client, auth_headers):
        """Non-image files should be rejected."""
        headers = auth_headers(username="upload_bad", email="upload_bad@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Upload Test",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        owner_id = create_resp.json()["user_id"]

        from app.auth import create_token
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        # Send a text file disguised as image
        resp = client.post(
            f"/api/contacts/{cid}/photos",
            headers=owner_headers,
            files={"file": ("malicious.txt", b"This is not an image", "text/plain")},
        )
        assert resp.status_code in [400, 422]

    def test_reject_oversized_file(self, client, auth_headers):
        """Files exceeding size limit should be rejected."""
        headers = auth_headers(username="upload_big", email="upload_big@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Big Upload",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        owner_id = create_resp.json()["user_id"]

        from app.auth import create_token
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        # Create a large file (6MB)
        large_data = b"\x00" * (6 * 1024 * 1024)
        resp = client.post(
            f"/api/contacts/{cid}/photos",
            headers=owner_headers,
            files={"file": ("large.jpg", large_data, "image/jpeg")},
        )
        assert resp.status_code in [400, 413, 422]

    def test_reject_invalid_jpeg_magic_bytes(self, client, auth_headers):
        """Files without JPEG magic bytes should be rejected."""
        headers = auth_headers(username="upload_fake", email="upload_fake@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Fake JPEG",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        owner_id = create_resp.json()["user_id"]

        from app.auth import create_token
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        # Fake JPEG — wrong magic bytes
        fake_jpeg = b"\x89PNG\r\n\x1a\n" + b"\x00" * 1000
        resp = client.post(
            f"/api/contacts/{cid}/photos",
            headers=owner_headers,
            files={"file": ("fake.jpg", fake_jpeg, "image/jpeg")},
        )
        assert resp.status_code in [400, 422]

    def test_max_photos_per_contact(self, client, auth_headers):
        """Should enforce max 5 photos per contact."""
        headers = auth_headers(username="upload_max", email="upload_max@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Max Photos",
            "phone": "1234567",
        })
        cid = create_resp.json()["id"]
        owner_id = create_resp.json()["user_id"]

        from app.auth import create_token
        from PIL import Image
        token = create_token(owner_id)
        owner_headers = {"Authorization": f"Bearer {token}"}

        # Create a valid small JPEG
        img_buffer = BytesIO()
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(img_buffer, format="JPEG")
        img_buffer.seek(0)
        img_data = img_buffer.getvalue()

        # Upload 5 photos
        for i in range(5):
            img_buffer = BytesIO()
            img = Image.new("RGB", (100, 100), color=(i * 50, 100, 100))
            img.save(img_buffer, format="JPEG")
            img_buffer.seek(0)
            resp = client.post(
                f"/api/contacts/{cid}/photos",
                headers=owner_headers,
                files={"file": (f"photo{i}.jpg", img_buffer.getvalue(), "image/jpeg")},
            )
            assert resp.status_code == 201, f"Photo {i} failed: {resp.text}"

        # 6th photo should be rejected
        img_buffer = BytesIO()
        img = Image.new("RGB", (100, 100), color="red")
        img.save(img_buffer, format="JPEG")
        img_buffer.seek(0)
        resp = client.post(
            f"/api/contacts/{cid}/photos",
            headers=owner_headers,
            files={"file": ("photo5.jpg", img_buffer.getvalue(), "image/jpeg")},
        )
        assert resp.status_code in [400, 422]


# ===========================================================================
# SPECIAL CHARACTERS
# ===========================================================================

class TestSpecialCharacters:
    """Test handling of special and edge-case characters."""

    def test_sql_keywords_in_name(self, client, auth_headers):
        """SQL keywords in name should be stored literally, not executed."""
        headers = auth_headers(username="sql_name", email="sql_name@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "DROP TABLE contacts; --",
            "phone": "1234567",
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "DROP TABLE contacts; --"

    def test_html_in_all_text_fields(self, client, auth_headers):
        """HTML in all text fields should be escaped."""
        headers = auth_headers(username="html_all", email="html_all@test.com")
        html_payload = "<script>alert('xss')</script>"
        resp = client.post("/api/contacts", headers=headers, json={
            "name": html_payload,
            "phone": "1234567",
            "description": html_payload,
            "address": html_payload,
            "city": html_payload,
            "neighborhood": html_payload,
            "about": html_payload,
        })
        assert resp.status_code == 201
        data = resp.json()
        for field in ["name", "description", "address", "city", "neighborhood", "about"]:
            assert "<script>" not in data.get(field, ""), f"XSS in {field}"

    def test_emoji_in_all_fields(self, client, auth_headers):
        """Emoji should be preserved in all text fields."""
        headers = auth_headers(username="emoji_test", email="emoji@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "🔧 Plomero 🚿",
            "phone": "1234567",
            "description": "⭐⭐⭐⭐⭐",
        })
        assert resp.status_code == 201
        assert "🔧" in resp.json()["name"]

    def test_zero_width_characters(self, client, auth_headers):
        """Zero-width characters should be handled."""
        headers = auth_headers(username="zw_test", email="zw@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test\u200BName",  # Zero-width space
            "phone": "1234567",
        })
        assert resp.status_code == 201

    def test_rtl_override_characters(self, client, auth_headers):
        """RTL override characters should be handled."""
        headers = auth_headers(username="rtl_test", email="rtl@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test\u202EName",  # RTL override
            "phone": "1234567",
        })
        assert resp.status_code == 201

    def test_control_characters(self, client, auth_headers):
        """Control characters should be handled gracefully."""
        headers = auth_headers(username="ctrl_test", email="ctrl@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Test\x01\x02\x03Name",
            "phone": "1234567",
        })
        assert resp.status_code in [201, 422]

    def test_very_long_unicode_string(self, client, auth_headers):
        """Very long unicode string should respect max_length."""
        headers = auth_headers(username="long_uni", email="long_uni@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "ñ" * 200,
            "phone": "1234567",
        })
        assert resp.status_code == 422  # Exceeds max_length=100


# ===========================================================================
# ERROR HANDLING
# ===========================================================================

class TestErrorHandling:
    """Test error handling robustness."""

    def test_malformed_json_returns_422(self, client, auth_headers):
        """Malformed JSON should return 422, not 500."""
        headers = auth_headers(username="malformed", email="malformed@test.com")
        resp = client.post(
            "/api/contacts",
            headers=headers,
            content=b"{invalid json}",
        )
        assert resp.status_code in [400, 422]

    def test_empty_body_returns_422(self, client, auth_headers):
        """Empty body should return 422."""
        headers = auth_headers(username="empty_body", email="empty_body@test.com")
        resp = client.post(
            "/api/contacts",
            headers=headers,
            content=b"",
        )
        assert resp.status_code in [400, 422]

    def test_wrong_content_type(self, client, auth_headers):
        """Wrong content type should be handled."""
        headers = auth_headers(username="wrong_ct", email="wrong_ct@test.com")
        resp = client.post(
            "/api/contacts",
            headers={**headers, "Content-Type": "text/plain"},
            content="name=Test&phone=123",
        )
        assert resp.status_code in [400, 422]

    def test_global_error_handler_returns_json(self, client):
        """Global error handler should return JSON, not HTML."""
        resp = client.get("/api/contacts/search?q=" + "A" * 100000)
        # Should not return HTML error page
        content_type = resp.headers.get("content-type", "")
        if resp.status_code == 500:
            assert "json" in content_type.lower() or "application" in content_type.lower()

    def test_404_returns_json_for_api(self, client):
        """API 404 should return JSON."""
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404
        # FastAPI returns JSON for API routes
        content_type = resp.headers.get("content-type", "")
        assert "json" in content_type.lower()
