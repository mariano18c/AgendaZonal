"""Advanced SQL injection tests specific to SQLite and SQLAlchemy."""
import pytest


class TestSQLiteSpecificInjection:

    @pytest.mark.security
    def test_sqlite_master_access_via_search(self, client):
        payloads = [
            "' UNION SELECT name, sql, '', '', '', '', '', '', '' FROM sqlite_master --",
            "' UNION SELECT * FROM sqlite_master --",
            "'; SELECT name FROM sqlite_master; --",
        ]
        for payload in payloads:
            resp = client.get(f"/api/contacts/search?q={payload}")
            assert resp.status_code == 200
            for item in resp.json():
                assert "sqlite_master" not in str(item).lower()
                assert "CREATE TABLE" not in str(item)

    @pytest.mark.security
    def test_union_select_injection(self, client, auth_headers):
        h = auth_headers(username="uniontest", email="union@test.com")
        client.post("/api/contacts", headers=h, json={
            "name": "Legit", "phone": "1234567",
        })

        payloads = [
            "' UNION SELECT id, username, email, password_hash, '', '', '', '', '' FROM users --",
            "' UNION SELECT 1,2,3,4,5,6,7,8,9 --",
        ]
        for payload in payloads:
            resp = client.get(f"/api/contacts/search?q={payload}")
            assert resp.status_code == 200
            for item in resp.json():
                assert "password_hash" not in str(item)

    @pytest.mark.security
    def test_boolean_blind_injection(self, client, auth_headers):
        h = auth_headers(username="blindtest", email="blind@test.com")
        client.post("/api/contacts", headers=h, json={
            "name": "Exists", "phone": "1234567",
        })

        payloads = [
            "' AND 1=1 --",
            "' AND 1=2 --",
            "' OR 1=1 --",
            "' OR 1=2 --",
            "' AND (SELECT COUNT(*) FROM users) > 0 --",
        ]
        for payload in payloads:
            resp = client.get(f"/api/contacts/search?q={payload}")
            assert resp.status_code == 200

    @pytest.mark.security
    def test_comment_based_injection(self, client):
        payloads = [
            "'/**/OR/**/1=1 --",
            "'/*comment*/OR/*comment*/1=1 --",
            "admin'--",
            "admin'/*",
        ]
        for payload in payloads:
            resp = client.post("/api/auth/login", json={
                "username_or_email": payload,
                "password": "anything",
            })
            assert resp.status_code == 401

    @pytest.mark.security
    def test_like_wildcard_abuse(self, client, auth_headers):
        h = auth_headers(username="wildcard", email="wildcard@test.com")
        client.post("/api/contacts", headers=h, json={
            "name": "Test Contact", "phone": "1234567",
        })

        payloads = ["%", "_", "%%", "%_%", "___"]
        for payload in payloads:
            resp = client.get(f"/api/contacts/search?q={payload}")
            assert resp.status_code == 200


class TestParameterizedQueryVerification:

    @pytest.mark.security
    def test_login_with_single_quotes_in_password(self, client):
        client.post("/api/auth/register", json={
            "username": "quotetest",
            "email": "quote@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "pass'word'123",
        })
        resp = client.post("/api/auth/login", json={
            "username_or_email": "quotetest",
            "password": "pass'word'123",
        })
        assert resp.status_code == 200

    @pytest.mark.security
    def test_contact_name_with_sql_keywords(self, client, auth_headers):
        h = auth_headers(username="sqlname", email="sqlname@test.com")
        resp = client.post("/api/contacts", headers=h, json={
            "name": "DROP TABLE contacts",
            "phone": "1234567",
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "DROP TABLE contacts"

    @pytest.mark.security
    def test_category_id_string_injection(self, client, auth_headers):
        h = auth_headers(username="catidtest", email="catid@test.com")
        resp = client.get("/api/contacts?category_id=1%20OR%201=1")
        assert resp.status_code in [200, 422]
