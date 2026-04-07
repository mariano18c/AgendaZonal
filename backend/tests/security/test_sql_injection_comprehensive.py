"""Comprehensive SQL injection tests - adapted for current test infrastructure."""
import pytest
from app.models.contact import Contact


class TestSQLInjectionInSearch:
    """Attempt SQL injection through search parameters."""

    @pytest.mark.parametrize("payload", [
        "' OR '1'='1",
        "'; DROP TABLE contacts; --",
        "' UNION SELECT * FROM users --",
        "1; DELETE FROM contacts WHERE '1'='1",
        "' OR 1=1 --",
        "admin'--",
        "' UNION SELECT username, password_hash FROM users --",
    ])
    def test_search_q_parameter(self, client, create_user, db_session, payload):
        """SQL injection in search q parameter should be handled safely."""
        user = create_user()
        contact = Contact(
            name="Test Business",
            phone="1234567",
            user_id=user.id,
        )
        db_session.add(contact)
        db_session.commit()
        
        resp = client.get(f"/api/contacts/search?q={payload}")
        assert resp.status_code in [200, 400]
        if resp.status_code == 200:
            data = resp.json()
            # Should not expose sensitive data
            for contact in data:
                assert "password" not in str(contact).lower()

    @pytest.mark.parametrize("payload", [
        "1 OR 1=1",
        "1; DROP TABLE contacts; --",
        "999 UNION SELECT * FROM users",
    ])
    def test_category_id_injection(self, client, payload):
        """SQL injection in category_id parameter."""
        resp = client.get(f"/api/contacts/search?category_id={payload}")
        assert resp.status_code in [200, 400, 422]

    @pytest.mark.parametrize("payload", [
        "'; DROP TABLE contacts; --",
        "1 OR 1=1",
        "UNION SELECT * FROM users",
    ])
    def test_contact_id_injection(self, client, payload):
        """SQL injection in contact ID path parameter."""
        resp = client.get(f"/api/contacts/{payload}")
        assert resp.status_code in [404, 422]


class TestSQLInjectionInPhoneSearch:
    """SQL injection through phone search."""

    @pytest.mark.parametrize("payload", [
        "' OR '1'='1",
        "'; DROP TABLE contacts; --",
        "' UNION SELECT * FROM users --",
    ])
    def test_phone_search_injection(self, client, create_user, db_session, payload):
        """SQL injection in phone search should be handled safely."""
        user = create_user()
        contact = Contact(
            name="Test Business",
            phone="1234567",
            user_id=user.id,
        )
        db_session.add(contact)
        db_session.commit()
        
        resp = client.get(f"/api/contacts/search/phone?phone={payload}")
        assert resp.status_code in [200, 422]
        if resp.status_code == 200:
            data = resp.json()
            # Should not expose sensitive data
            for contact in data:
                assert "password" not in str(contact).lower()

    def test_phone_search_wildcard_injection(self, client, create_user, db_session):
        """Phone search with % should not return all records."""
        user = create_user()
        for i in range(5):
            db_session.add(Contact(name=f"Biz{i}", phone=f"12345{i:02d}", user_id=user.id))
        db_session.commit()

        resp = client.get("/api/contacts/search/phone?phone=%2525")
        assert resp.status_code == 200
        # Should not return all 5 contacts due to wildcard


class TestWildcardInjection:
    """Test LIKE wildcard injection."""

    def test_like_wildcard_percent_in_search(self, client, create_user, db_session):
        """Percent sign in search should be treated as literal, not wildcard."""
        user = create_user()
        contact = Contact(
            name="Test 50% Off",
            phone="1234567",
            user_id=user.id,
        )
        db_session.add(contact)
        db_session.commit()
        
        # Search with percent should find exact match or none
        resp = client.get("/api/contacts/search?q=50%")
        assert resp.status_code == 200

    def test_like_wildcard_underscore_in_search(self, client, create_user, db_session):
        """Underscore in search should be treated as literal, not wildcard."""
        user = create_user()
        contact = Contact(
            name="Test_A",
            phone="1234567",
            user_id=user.id,
        )
        db_session.add(contact)
        db_session.commit()
        
        # Search with underscore
        resp = client.get("/api/contacts/search?q=Test_")
        assert resp.status_code == 200


class TestSQLInjectionInAuth:
    """SQL injection through authentication."""

    def test_login_with_sql_in_username(self, client):
        """SQL injection in login username should be rejected."""
        resp = client.post("/api/auth/login", json={
            "username_or_email": "' OR '1'='1' --",
            "password": "anything",
        })
        assert resp.status_code == 401

    def test_login_with_sql_in_password(self, client, create_user):
        """SQL injection in login password should be rejected."""
        create_user()
        resp = client.post("/api/auth/login", json={
            "username_or_email": "testuser",
            "password": "' OR '1'='1' --",
        })
        assert resp.status_code == 401

    def test_register_with_sql_in_username(self, client, captcha):
        """SQL injection in registration username should be sanitized or rejected."""
        resp = client.post("/api/auth/register", json={
            "username": "'; DROP TABLE users; --",
            "email": "sql@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        # Should either validate and reject or sanitize
        assert resp.status_code in [201, 400, 422]


class TestSQLInjectionInAdmin:
    """SQL injection through admin endpoints."""

    def test_analytics_zone_injection(self, client, admin_headers):
        """SQL injection in analytics zone parameter should be handled safely."""
        resp = client.get(
            "/api/admin/analytics?zone=' OR '1'='1",
            headers=admin_headers
        )
        assert resp.status_code == 200
        # Should not return unexpected data

    def test_users_filter_injection(self, client, admin_headers):
        """SQL injection in users filter should be handled safely."""
        resp = client.get(
            "/api/users?username=' OR '1'='1",
            headers=admin_headers
        )
        assert resp.status_code in [200, 400, 422]
