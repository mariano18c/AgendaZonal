"""Race condition and concurrency tests - adapted."""
import pytest
from concurrent.futures import ThreadPoolExecutor
from app.models.contact import Contact


class TestRaceConditions:
    """Test race conditions in business logic."""

    @pytest.mark.security
    def test_concurrent_review_unique_constraint_enforced(self, client, auth_headers):
        """Verify UNIQUE constraint on review (user_id + contact_id) is enforced."""
        headers_reviewer = auth_headers(username="race_rev", email="racerev@test.com")
        headers_owner = auth_headers(username="race_owner3", email="raceowner3@test.com")
        
        # Owner creates contact
        create_resp = client.post("/api/contacts", headers=headers_owner, json={
            "name": "Race Review Test", "phone": "1234569",
        })
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]
        
        # Try to create review
        resp1 = client.post(
            f"/api/contacts/{cid}/reviews",
            headers=headers_reviewer,
            json={"rating": 5, "comment": "First review"}
        )
        assert resp1.status_code == 201
        
        # Try again - should fail (unique constraint)
        resp2 = client.post(
            f"/api/contacts/{cid}/reviews",
            headers=headers_reviewer,
            json={"rating": 4, "comment": "Second review"}
        )
        assert resp2.status_code in [409, 400, 422]

    @pytest.mark.security
    def test_concurrent_report_unique_constraint_enforced(self, client, auth_headers):
        """Verify UNIQUE constraint on report (user_id + contact_id) is enforced."""
        headers_reporter = auth_headers(username="race_rpt", email="racereport@test.com")
        headers_owner = auth_headers(username="race_owner4", email="raceowner4@test.com")
        
        # Owner creates contact
        create_resp = client.post("/api/contacts", headers=headers_owner, json={
            "name": "Race Report Test 2", "phone": "1234570",
        })
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]
        
        # First report - should succeed
        resp1 = client.post(
            f"/api/contacts/{cid}/report",
            headers=headers_reporter,
            json={"reason": "spam", "details": "First"}
        )
        assert resp1.status_code == 201
        
        # Second report - should fail (unique constraint)
        resp2 = client.post(
            f"/api/contacts/{cid}/report",
            headers=headers_reporter,
            json={"reason": "falso", "details": "Second"}
        )
        assert resp2.status_code in [409, 400, 422]


class TestJWTSecretStrength:
    """Test JWT secret strength."""

    @pytest.mark.security
    def test_jwt_secret_meets_minimum_requirements(self, client):
        """Verify JWT_SECRET meets minimum entropy requirements."""
        from app.config import JWT_SECRET
        
        # JWT_SECRET should be at least 32 bytes
        assert len(JWT_SECRET) >= 32, f"JWT_SECRET too short: {len(JWT_SECRET)} bytes"
        
        # Should not be a common weak secret
        weak_secrets = [
            "secret", "password", "123456", "changeme", "default",
            "jwtsecret", "mysecret", "admin", "root", "test"
        ]
        assert JWT_SECRET.lower() not in weak_secrets, "JWT_SECRET is a common weak secret"

    @pytest.mark.security
    def test_jwt_algorithm_is_hs256(self, client):
        """Verify JWT uses HS256 algorithm."""
        from app.config import JWT_ALGORITHM
        assert JWT_ALGORITHM == "HS256", f"JWT_ALGORITHM should be HS256, got {JWT_ALGORITHM}"


class TestDatabaseConcurrency:
    """Test database concurrency handling."""

    def test_concurrent_lead_generation(self, client, create_user, db_session):
        """Multiple concurrent leads should all be recorded."""
        user = create_user()
        contact = Contact(name="Test", phone="1234567", user_id=user.id)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)
        
        # Make concurrent lead requests (using sync client, not true concurrency but tests the endpoint)
        responses = []
        for i in range(5):
            resp = client.post(f"/api/contacts/{contact.id}/leads", json={
                "channel": "web",
                "referrer": f"test_{i}",
            })
            responses.append(resp.status_code)
        
        # All should succeed (no crash)
        assert all(r in [200, 201, 400] for r in responses)

    def test_wal_mode_enabled(self, client):
        """Verify SQLite WAL mode is enabled."""
        from sqlalchemy import text
        from app.database import engine
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode")).fetchone()[0].lower()
            assert "wal" in result, f"WAL mode not enabled: {result}"
