"""Security tests: SQL injection, XSS, path traversal, auth bypass, input validation.

Expanded with:
- Additional fuzzing payloads
- Token with deactivated user
- Protected fields verification
- Error message safety
"""
import pytest
import io


class TestSQLInjection:

    @pytest.mark.security
    def test_search_no_sql_injection(self, client):
        payloads = [
            "'; DROP TABLE contacts; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO users VALUES(999,'hacked','h@ck.com','000','000','hash','admin',1); --",
        ]
        for payload in payloads:
            resp = client.get(f"/api/contacts/search?q={payload}")
            assert resp.status_code == 200

    @pytest.mark.security
    def test_login_no_sql_injection(self, client):
        resp = client.post("/api/auth/login", json={
            "username_or_email": "' OR 1=1 --",
            "password": "anything",
        })
        assert resp.status_code == 401

    @pytest.mark.security
    def test_register_no_sql_injection(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "'; DROP TABLE users; --",
            "email": "sql@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
        })
        assert resp.status_code in [201, 400, 422]

    @pytest.mark.security
    def test_contact_id_sql_injection(self, client):
        resp = client.get("/api/contacts/1%20OR%201=1")
        assert resp.status_code in [404, 422]

    @pytest.mark.security
    def test_category_filter_sql_injection(self, client):
        resp = client.get("/api/contacts?category_id=1%20OR%201=1")
        assert resp.status_code in [200, 422]

    @pytest.mark.security
    def test_like_wildcard_injection_in_search(self, client, auth_headers):
        """Ensure % and _ in search queries don't cause unexpected results."""
        h = auth_headers(username="likeuser", email="like@test.com")
        client.post("/api/contacts", headers=h, json={
            "name": "ExactMatch", "phone": "1234567",
        })

        resp = client.get("/api/contacts/search?q=%25")
        assert resp.status_code == 200

        resp = client.get("/api/contacts/search?q=_%")
        assert resp.status_code == 200


class TestXSSPrevention:

    @pytest.mark.security
    def test_script_in_contact_name(self, client, auth_headers):
        headers = auth_headers(username="xssuser1", email="xss1@test.com")
        xss = '<script>alert("xss")</script>'
        resp = client.post("/api/contacts", headers=headers, json={
            "name": xss,
            "phone": "1234567",
        })
        assert resp.status_code == 201
        # Sanitized: HTML entities escaped
        assert "<script>" not in resp.json()["name"]
        assert "&lt;script&gt;" in resp.json()["name"]

    @pytest.mark.security
    def test_script_in_description(self, client, auth_headers):
        headers = auth_headers(username="xssuser2", email="xss2@test.com")
        xss = '<img src=x onerror=alert(1)>'
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Valid Name",
            "phone": "1234567",
            "description": xss,
        })
        assert resp.status_code == 201

    @pytest.mark.security
    def test_script_in_username(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "<script>alert('xss')</script>",
            "email": "xssuser@test.com",
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": "password123",
        })
        assert resp.status_code in [201, 400, 422]


class TestPathTraversal:

    @pytest.mark.security
    def test_relative_path_traversal(self, client):
        resp = client.get("/../../../etc/passwd")
        assert resp.status_code in [403, 404]

    @pytest.mark.security
    def test_encoded_path_traversal(self, client):
        resp = client.get("/%2e%2e/%2e%2e/etc/passwd")
        assert resp.status_code in [403, 404]

    @pytest.mark.security
    def test_html_route_traversal(self, client):
        resp = client.get("/../../../etc/passwd.html")
        assert resp.status_code in [403, 404]


class TestAuthBypass:

    @pytest.mark.security
    def test_access_protected_without_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    @pytest.mark.security
    def test_access_with_tampered_token(self, client):
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.invalid"
        })
        assert resp.status_code == 401

    @pytest.mark.security
    def test_access_with_empty_bearer(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401

    @pytest.mark.security
    def test_user_cannot_access_admin_endpoints(self, client, admin_headers, auth_headers):
        """A non-admin user cannot list users."""
        # admin_headers is from the first registered user (admin)
        h_user = auth_headers(username="secnormal", email="secnorm@test.com")
        resp = client.get("/api/users", headers=h_user)
        assert resp.status_code == 403

    @pytest.mark.security
    def test_non_owner_cannot_delete_contact(self, client, auth_headers):
        h_owner = auth_headers(username="seclowner", email="seclown@test.com")
        h_other = auth_headers(username="seclother", email="secloth@test.com")

        create = client.post("/api/contacts", headers=h_owner, json={
            "name": "Protected", "phone": "1234567",
        })
        cid = create.json()["id"]

        resp = client.delete(f"/api/contacts/{cid}", headers=h_other)
        assert resp.status_code == 403

    @pytest.mark.security
    def test_mod_can_verify_contact(self, client, auth_headers, moderator_user, contact_factory):
        h_owner = auth_headers(username="modverowner", email="modver@test.com")
        mod_user, h_mod = moderator_user

        cid = contact_factory(h_owner, name="Verifiable", phone="1234567")

        resp = client.post(
            f"/api/contacts/{cid}/verify",
            headers=h_mod,
            json={"is_verified": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_verified"] is True

    @pytest.mark.security
    def test_deactivated_user_token_rejected(self, client, create_user, database_session):
        """A token from a user that was later deactivated should be rejected."""
        user = create_user(username="deactoken", email="deact@test.com")
        database_session.commit()

        # Generate token directly (login would fail with default hash)
        from app.auth import create_token
        token = create_token(user.id)

        # Deactivate the user
        user.is_active = False
        database_session.commit()

        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "inactivo" in resp.json()["detail"].lower()


class TestInputValidation:

    @pytest.mark.security
    def test_extremely_long_name(self, client, auth_headers):
        headers = auth_headers(username="longname", email="longname@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "A" * 500,
            "phone": "1234567",
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_extremely_long_description(self, client, auth_headers):
        headers = auth_headers(username="longdesc", email="longdesc@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Valid",
            "phone": "1234567",
            "description": "X" * 1000,
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_negative_latitude(self, client, auth_headers):
        headers = auth_headers(username="neglat", email="neglat@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Valid",
            "phone": "1234567",
            "latitude": -95.0,
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_longitude_out_of_range(self, client, auth_headers):
        headers = auth_headers(username="badlon", email="badlon@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Valid",
            "phone": "1234567",
            "longitude": 200.0,
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_phone_with_special_chars(self, client, auth_headers):
        headers = auth_headers(username="badphone", email="badphone@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Valid",
            "phone": "phone<script>alert(1)</script>",
        })
        assert resp.status_code == 422

    @pytest.mark.security
    def test_missing_required_fields(self, client, auth_headers):
        headers = auth_headers(username="missing", email="missing@test.com")
        resp = client.post("/api/contacts", headers=headers, json={})
        assert resp.status_code == 422

    @pytest.mark.security
    def test_invalid_json_body(self, client, auth_headers):
        headers = auth_headers(username="badjson", email="badjson@test.com")
        headers_no_ct = {"Authorization": headers["Authorization"]}
        resp = client.post(
            "/api/contacts",
            headers=headers_no_ct,
            content=b"not json at all",
        )
        assert resp.status_code == 422


class TestErrorMessages:

    @pytest.mark.security
    def test_login_error_no_user_enumeration(self, client):
        resp = client.post("/api/auth/login", json={
            "username_or_email": "nonexistent@test.com",
            "password": "wrong",
        })
        assert resp.status_code == 401
        detail = resp.json()["detail"].lower()
        assert "no existe" not in detail
        assert "not found" not in detail

    @pytest.mark.security
    def test_404_no_internal_info(self, client):
        resp = client.get("/api/contacts/99999")
        assert resp.status_code == 404
        detail = resp.json()["detail"].lower()
        assert "traceback" not in detail
        assert "sqlalchemy" not in detail

    @pytest.mark.security
    def test_403_no_role_details_leaked(self, client, auth_headers):
        h1 = auth_headers(username="leak1", email="leak1@test.com")
        h2 = auth_headers(username="leak2", email="leak2@test.com")
        create = client.post("/api/contacts", headers=h1, json={
            "name": "Secret", "phone": "1234567",
        })
        cid = create.json()["id"]
        resp = client.delete(f"/api/contacts/{cid}", headers=h2)
        assert resp.status_code == 403
        detail = resp.json()["detail"].lower()
        assert "role" not in detail or "permisos" in detail


class TestProtectedFields:

    @pytest.mark.security
    def test_no_editar_is_verified_directamente(self, client, auth_headers):
        headers = auth_headers(username="protuser", email="prot@test.com")
        create = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1234567",
        })
        cid = create.json()["id"]

        resp = client.put(f"/api/contacts/{cid}", headers=headers, json={
            "is_verified": True,
            "verified_by": 1,
        })
        assert resp.status_code == 200
        assert resp.json()["is_verified"] is False

    @pytest.mark.security
    def test_no_editar_user_id_directamente(self, client, auth_headers):
        headers = auth_headers(username="prot2user", email="prot2@test.com")
        create = client.post("/api/contacts", headers=headers, json={
            "name": "Test",
            "phone": "1234567",
        })
        cid = create.json()["id"]
        original_user_id = create.json()["user_id"]

        resp = client.put(f"/api/contacts/{cid}", headers=headers, json={
            "user_id": 999,
        })
        assert resp.status_code == 200
        assert resp.json()["user_id"] == original_user_id
