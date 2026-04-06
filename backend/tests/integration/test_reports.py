"""Integration tests — Reports (report, auto-flag, resolve)."""
import pytest
from tests.conftest import _bearer


class TestReportContact:
    def test_report_success(self, client, create_user, create_contact):
        reporter = create_user()
        c = create_contact()
        r = client.post(f"/api/contacts/{c.id}/report",
                         headers=_bearer(reporter),
                         json={"reason": "spam", "details": "Es spam"})
        assert r.status_code == 201

    def test_report_invalid_reason(self, client, create_user, create_contact):
        reporter = create_user()
        c = create_contact()
        r = client.post(f"/api/contacts/{c.id}/report",
                         headers=_bearer(reporter),
                         json={"reason": "invalid"})
        assert r.status_code == 422

    def test_report_duplicate(self, client, create_user, create_contact):
        reporter = create_user()
        c = create_contact()
        client.post(f"/api/contacts/{c.id}/report",
                     headers=_bearer(reporter),
                     json={"reason": "spam"})
        r = client.post(f"/api/contacts/{c.id}/report",
                         headers=_bearer(reporter),
                         json={"reason": "spam"})
        assert r.status_code in (400, 409)

    def test_report_unauthenticated(self, client, create_contact):
        c = create_contact()
        r = client.post(f"/api/contacts/{c.id}/report",
                         json={"reason": "spam"})
        assert r.status_code == 401

    def test_auto_flag_after_3_reports(self, client, create_contact, create_user):
        c = create_contact()
        for _ in range(3):
            user = create_user()
            client.post(f"/api/contacts/{c.id}/report",
                         headers=_bearer(user),
                         json={"reason": "spam"})
        # Contact should be flagged
        r = client.get(f"/api/contacts/{c.id}")
        assert r.json()["status"] == "flagged"


class TestResolveReport:
    def test_resolve_report(self, client, mod_headers, create_contact, create_report):
        c = create_contact()
        report = create_report(contact_id=c.id)
        r = client.post(f"/api/admin/reports/{report.id}/resolve",
                          headers=mod_headers, params={"action": "reactivate"})
        assert r.status_code == 200
        assert r.json().get("new_status") == "active" or "contact_id" in r.json()

    def test_resolve_nonexistent(self, client, mod_headers):
        r = client.post("/api/admin/reports/99999/resolve", headers=mod_headers, params={"action": "reactivate"})
        assert r.status_code == 404

    def test_resolve_as_regular_user(self, client, user_headers, create_contact, create_report):
        c = create_contact()
        report = create_report(contact_id=c.id)
        r = client.post(f"/api/admin/reports/{report.id}/resolve",
                          headers=user_headers, params={"action": "reactivate"})
        assert r.status_code == 403


class TestAdminReportLists:
    def test_list_pending_reports(self, client, mod_headers, create_contact, create_report):
        c = create_contact()
        create_report(contact_id=c.id)
        r = client.get("/api/admin/reports/pending", headers=mod_headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_list_flagged_contacts(self, client, mod_headers, create_contact):
        create_contact(status="flagged")
        r = client.get("/api/admin/reports/flagged", headers=mod_headers)
        assert r.status_code == 200
