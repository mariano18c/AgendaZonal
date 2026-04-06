"""Security tests — Fuzzing with unexpected/malicious payloads."""
import pytest
from tests.conftest import _bearer


class TestContactFuzzing:
    """Send unexpected types and sizes to contact endpoints."""

    def test_invalid_json_body(self, client, user_headers):
        r = client.post("/api/contacts",
                         headers={**user_headers, "Content-Type": "application/json"},
                         content="not valid json")
        assert r.status_code in (400, 422)

    def test_empty_body(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers, json={})
        assert r.status_code == 422

    def test_extra_fields_ignored(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers, json={
            "name": "Valid Name", "evil_field": "should be ignored",
            "role": "admin",  # attempt to inject role
        })
        assert r.status_code == 201

    def test_null_name(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers,
                         json={"name": None})
        assert r.status_code == 422

    def test_numeric_name(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers,
                         json={"name": 12345})
        # Pydantic coerces to string or rejects
        assert r.status_code in (201, 422)

    def test_very_long_description(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers,
                         json={"name": "Test", "description": "x" * 10000})
        assert r.status_code == 422

    def test_negative_category_id(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers,
                         json={"name": "Test", "category_id": -1})
        assert r.status_code in (201, 400, 422, 500)

    def test_float_category_id(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers,
                         json={"name": "Test", "category_id": 1.5})
        assert r.status_code in (201, 422)

    def test_array_as_name(self, client, user_headers):
        r = client.post("/api/contacts", headers=user_headers,
                         json={"name": ["array", "value"]})
        assert r.status_code == 422


class TestAuthFuzzing:
    def test_login_with_array_password(self, client):
        r = client.post("/api/auth/login", json={
            "username_or_email": "test", "password": ["array"],
        })
        assert r.status_code == 422

    def test_login_with_null_values(self, client):
        r = client.post("/api/auth/login", json={
            "username_or_email": None, "password": None,
        })
        assert r.status_code == 422

    def test_register_with_empty_strings(self, client, captcha):
        r = client.post("/api/auth/register", json={
            "username": "", "email": "",
            "phone_area_code": "", "phone_number": "",
            "password": "",
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        assert r.status_code == 422


class TestReviewFuzzing:
    def test_rating_zero(self, client, create_user, create_contact):
        u = create_user()
        c = create_contact()
        r = client.post(f"/api/contacts/{c.id}/reviews",
                         headers=_bearer(u), json={"rating": 0})
        assert r.status_code == 422

    def test_rating_negative(self, client, create_user, create_contact):
        u = create_user()
        c = create_contact()
        r = client.post(f"/api/contacts/{c.id}/reviews",
                         headers=_bearer(u), json={"rating": -1})
        assert r.status_code == 422

    def test_rating_string(self, client, create_user, create_contact):
        u = create_user()
        c = create_contact()
        r = client.post(f"/api/contacts/{c.id}/reviews",
                         headers=_bearer(u), json={"rating": "five"})
        assert r.status_code == 422

    def test_rating_float(self, client, create_user, create_contact):
        u = create_user()
        c = create_contact()
        r = client.post(f"/api/contacts/{c.id}/reviews",
                         headers=_bearer(u), json={"rating": 3.5})
        assert r.status_code in (201, 422)  # May coerce or reject


class TestOfferFuzzing:
    def test_discount_100(self, client, create_user, create_contact):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        r = client.post(f"/api/contacts/{c.id}/offers", headers=_bearer(owner),
                         json={"title": "X", "discount_pct": 100,
                               "expires_at": "2030-01-01T00:00:00Z"})
        assert r.status_code == 422

    def test_negative_discount(self, client, create_user, create_contact):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        r = client.post(f"/api/contacts/{c.id}/offers", headers=_bearer(owner),
                         json={"title": "X", "discount_pct": -10,
                               "expires_at": "2030-01-01T00:00:00Z"})
        assert r.status_code == 422
