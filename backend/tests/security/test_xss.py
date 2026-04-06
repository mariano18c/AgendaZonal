"""Security tests — XSS / HTML injection prevention."""
import pytest
from tests.conftest import _bearer

XSS_PAYLOADS = [
    '<script>alert("xss")</script>',
    '<img src=x onerror=alert(1)>',
    '<svg onload=alert(1)>',
    '"><marquee onstart=alert(1)>',
    "javascript:alert('xss')",
    '<iframe src="data:text/html,<script>alert(1)</script>">',
    '<body onload=alert(1)>',
    '{{7*7}}',  # SSTI
    '${7*7}',   # Template injection
    '<a href="javascript:void(0)" onclick="alert(1)">click</a>',
]


class TestContactXSS:
    @pytest.mark.parametrize("payload", XSS_PAYLOADS[:5])
    def test_name_sanitized(self, client, user_headers, payload):
        r = client.post("/api/contacts", headers=user_headers,
                         json={"name": payload})
        if r.status_code == 201:
            name = r.json()["name"]
            # It should be either escaped or stripped of tags
            assert "&lt;" in name or "<" not in name

    @pytest.mark.parametrize("payload", XSS_PAYLOADS[:5])
    def test_description_sanitized(self, client, user_headers, payload):
        r = client.post("/api/contacts", headers=user_headers,
                         json={"name": "Safe", "description": payload})
        if r.status_code == 201:
            desc = r.json().get("description") or ""
            assert "&lt;" in desc or "<" not in desc

    def test_about_sanitized(self, client, user_headers):
        payload = '<img src=x onerror=alert(1)>'
        r = client.post("/api/contacts", headers=user_headers,
                         json={"name": "Safe", "about": payload})
        if r.status_code == 201:
            about = r.json().get("about") or ""
            assert "&lt;" in about or "<" not in about


class TestReviewXSS:
    @pytest.mark.parametrize("payload", XSS_PAYLOADS[:3])
    def test_review_comment_sanitized(self, client, create_user, create_contact, payload):
        reviewer = create_user()
        c = create_contact()
        r = client.post(f"/api/contacts/{c.id}/reviews",
                         headers=_bearer(reviewer),
                         json={"rating": 5, "comment": payload})
        if r.status_code == 201:
            comment = r.json().get("comment", "")
            assert "&lt;" in comment or "<" not in comment

    def test_reply_sanitized(self, client, create_user, create_contact, create_review):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        rev = create_review(contact_id=c.id, is_approved=True)
        r = client.post(f"/api/reviews/{rev.id}/reply", headers=_bearer(owner),
                         json={"reply_text": '<script>alert(1)</script>'})
        if r.status_code == 200:
            reply = r.json().get("reply_text", "")
            assert "&lt;" in reply or "<" not in reply


class TestReportXSS:
    def test_report_details_sanitized(self, client, create_user, create_contact):
        reporter = create_user()
        c = create_contact()
        r = client.post(f"/api/contacts/{c.id}/report",
                         headers=_bearer(reporter),
                         json={"reason": "spam", "details": '<script>alert(1)</script>'})
        if r.status_code == 201:
            details = r.json().get("details") or ""
            assert "&lt;" in details or "<" not in details
