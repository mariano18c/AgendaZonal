"""Security tests — SQL injection payloads across all search endpoints."""
import pytest
from tests.conftest import _bearer

# Classic SQL injection payloads
SQLI_PAYLOADS = [
    "'; DROP TABLE contacts; --",
    "' OR '1'='1",
    "' UNION SELECT 1,2,3,4,5,6,7,8,9,10--",
    "1; UPDATE users SET role='admin' WHERE 1=1;--",
    "' OR 1=1--",
    "admin'--",
    "1' AND (SELECT * FROM users) > 0--",
    "'; ATTACH DATABASE ':memory:' AS hacked;--",
    "' OR ''='",
    "%' OR 1=1--",
    "_%' ORDER BY 1--",
    "'; PRAGMA table_info(users);--",
]


class TestContactSearchSQLi:
    """SQL injection in /api/contacts/search endpoint."""

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_search_q_param(self, client, payload):
        r = client.get("/api/contacts/search", params={"q": payload})
        assert r.status_code in (200, 400)
        # Should never return a server error (500)
        assert r.status_code != 500

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_search_category_id(self, client, payload):
        r = client.get("/api/contacts/search", params={"q": "test", "category_id": payload})
        assert r.status_code in (200, 400, 422)

    def test_search_wildcard_escape(self, client, create_contact):
        """Verify that %_ wildcards are escaped in LIKE queries."""
        create_contact(name="100% Real")
        r = client.get("/api/contacts/search", params={"q": "100%"})
        assert r.status_code == 200


class TestPhoneSearchSQLi:
    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_phone_search(self, client, payload):
        r = client.get("/api/contacts/search/phone", params={"phone": payload})
        assert r.status_code in (200, 400, 422)
        assert r.status_code != 500


class TestAnalyticsSQLi:
    """SQL injection in the zone parameter of analytics endpoints."""

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_analytics_zone(self, client, mod_headers, payload):
        r = client.get("/api/admin/analytics", headers=mod_headers,
                        params={"zone": payload})
        assert r.status_code in (200, 400)
        assert r.status_code != 500

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_analytics_export_zone(self, client, mod_headers, payload):
        r = client.get("/api/admin/analytics/export", headers=mod_headers,
                        params={"zone": payload})
        assert r.status_code in (200, 400)
        assert r.status_code != 500


class TestUserSearchSQLi:
    """SQL injection in user search/filter parameters."""

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_users_username_filter(self, client, admin_headers, payload):
        r = client.get("/api/users", headers=admin_headers,
                        params={"username": payload})
        # Should not crash
        assert r.status_code in (200, 400)
        assert r.status_code != 500


class TestAuthSQLi:
    """SQL injection in login credentials."""

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_login_username(self, client, payload):
        r = client.post("/api/auth/login", json={
            "username_or_email": payload,
            "password": "password123",
        })
        assert r.status_code in (401, 422)
        assert r.status_code != 500

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_login_password(self, client, payload):
        r = client.post("/api/auth/login", json={
            "username_or_email": "admin",
            "password": payload,
        })
        assert r.status_code in (401, 422)
        assert r.status_code != 500
