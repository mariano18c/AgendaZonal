"""Integration tests for Phase 5: Reports, Analytics, Utilities."""
import pytest


class TestReports:
    """Test crowdsourced reports system."""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_headers, contact_factory, moderator_user):
        self.owner_headers = auth_headers(username="rpt_owner", email="rptowner@test.com")
        self.reporter1 = auth_headers(username="rpt_r1", email="rptr1@test.com")
        self.reporter2 = auth_headers(username="rpt_r2", email="rptr2@test.com")
        self.reporter3 = auth_headers(username="rpt_r3", email="rptr3@test.com")
        self.mod_user, self.mod_headers = moderator_user
        self.contact_id = contact_factory(
            self.owner_headers, name="Reported Contact", phone="3411111111",
            category_id=1,
        )

    def test_report_contact(self, client):
        resp = client.post(f"/api/contacts/{self.contact_id}/report",
            headers=self.reporter1,
            json={"reason": "spam", "details": "Este es spam"},
        )
        assert resp.status_code == 201
        assert resp.json()["reports_count"] == 1

    def test_duplicate_report(self, client):
        client.post(f"/api/contacts/{self.contact_id}/report",
            headers=self.reporter1, json={"reason": "spam"},
        )
        resp = client.post(f"/api/contacts/{self.contact_id}/report",
            headers=self.reporter1, json={"reason": "falso"},
        )
        assert resp.status_code == 409

    def test_self_report_blocked(self, client):
        resp = client.post(f"/api/contacts/{self.contact_id}/report",
            headers=self.owner_headers, json={"reason": "spam"},
        )
        assert resp.status_code == 400

    def test_auto_flag_at_3_reports(self, client):
        """3 distinct reports auto-flags the contact."""
        for headers in [self.reporter1, self.reporter2, self.reporter3]:
            client.post(f"/api/contacts/{self.contact_id}/report",
                headers=headers, json={"reason": "spam"},
            )
        contact = client.get(f"/api/contacts/{self.contact_id}").json()
        assert contact["status"] == "flagged"

    def test_mod_sees_flagged(self, client):
        """Moderator can list flagged contacts."""
        for h in [self.reporter1, self.reporter2, self.reporter3]:
            client.post(f"/api/contacts/{self.contact_id}/report", headers=h, json={"reason": "spam"})
        resp = client.get("/api/admin/reports/flagged", headers=self.mod_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_mod_resolves_reactivate(self, client):
        """Moderator reactivates a flagged contact."""
        for h in [self.reporter1, self.reporter2, self.reporter3]:
            client.post(f"/api/contacts/{self.contact_id}/report", headers=h, json={"reason": "spam"})
        # Get the first report id
        flagged = client.get("/api/admin/reports/flagged", headers=self.mod_headers).json()
        report_id = flagged["flagged"][0]["reports"][0]["id"]

        resp = client.post(f"/api/admin/reports/{report_id}/resolve",
            headers=self.mod_headers, params={"action": "reactivate"},
        )
        assert resp.status_code == 200
        assert resp.json()["new_status"] == "active"

    def test_mod_resolves_suspend(self, client):
        for h in [self.reporter1, self.reporter2, self.reporter3]:
            client.post(f"/api/contacts/{self.contact_id}/report", headers=h, json={"reason": "spam"})
        flagged = client.get("/api/admin/reports/flagged", headers=self.mod_headers).json()
        report_id = flagged["flagged"][0]["reports"][0]["id"]

        resp = client.post(f"/api/admin/reports/{report_id}/resolve",
            headers=self.mod_headers, params={"action": "suspend"},
        )
        assert resp.json()["new_status"] == "suspended"

    def test_non_mod_cannot_resolve(self, client):
        client.post(f"/api/contacts/{self.contact_id}/report", headers=self.reporter1, json={"reason": "spam"})
        resp = client.post("/api/admin/reports/1/resolve",
            headers=self.reporter1, params={"action": "reactivate"},
        )
        assert resp.status_code == 403

    def test_invalid_reason(self, client):
        resp = client.post(f"/api/contacts/{self.contact_id}/report",
            headers=self.reporter1, json={"reason": "invalid"},
        )
        assert resp.status_code == 422


class TestAnalytics:
    """Test analytics and CSV export."""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_headers, contact_factory, moderator_user):
        self.owner_headers = auth_headers(username="anl_owner", email="anlowner@test.com")
        self.mod_user, self.mod_headers = moderator_user
        self.contact_id = contact_factory(
            self.owner_headers, name="Anl Contact", phone="3411111111",
            category_id=1, city="Rosario",
        )

    def test_analytics_returns_data(self, client):
        resp = client.get("/api/admin/analytics", headers=self.mod_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_providers" in data
        assert "active_providers" in data
        assert "total_leads" in data
        assert "avg_rating" in data
        assert "top_categories" in data
        assert "leads_by_day" in data

    def test_analytics_with_zone(self, client):
        resp = client.get("/api/admin/analytics", headers=self.mod_headers, params={"zone": "Rosario"})
        assert resp.status_code == 200
        assert resp.json()["zone"] == "Rosario"

    def test_non_mod_cannot_see_analytics(self, client):
        resp = client.get("/api/admin/analytics", headers=self.owner_headers)
        assert resp.status_code == 403

    def test_csv_export(self, client):
        resp = client.get("/api/admin/analytics/export", headers=self.mod_headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "nombre" in resp.text  # CSV header


class TestUtilities:
    """Test utility items CRUD."""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_headers, moderator_user):
        # Regular user
        self.user_headers = auth_headers(username="utl_user", email="utluser@test.com")
        # Moderator (has admin/mod permissions for utilities)
        self.mod_user, self.mod_headers = moderator_user

    def test_create_utility(self, client):
        resp = client.post("/api/admin/utilities",
            headers=self.mod_headers,
            json={"type": "farmacia_turno", "name": "Farmacia Central", "phone": "3411234567", "schedule": "24hs", "city": "Rosario"},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Farmacia Central"

    def test_list_utilities_public(self, client):
        client.post("/api/admin/utilities",
            headers=self.mod_headers,
            json={"type": "emergencia", "name": "Hospital"},
        )
        resp = client.get("/api/utilities")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_list_utilities_filter_type(self, client):
        client.post("/api/admin/utilities", headers=self.mod_headers,
            json={"type": "farmacia_turno", "name": "Farmacia"})
        client.post("/api/admin/utilities", headers=self.mod_headers,
            json={"type": "emergencia", "name": "Hospital"})
        resp = client.get("/api/utilities", params={"type": "farmacia_turno"})
        items = resp.json()
        assert all(i["type"] == "farmacia_turno" for i in items)

    def test_update_utility(self, client):
        create_resp = client.post("/api/admin/utilities",
            headers=self.mod_headers,
            json={"name": "Old Name"},
        )
        item_id = create_resp.json()["id"]
        resp = client.put(f"/api/admin/utilities/{item_id}",
            headers=self.mod_headers,
            json={"name": "New Name", "type": "otro"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_delete_utility(self, client):
        create_resp = client.post("/api/admin/utilities",
            headers=self.mod_headers, json={"name": "ToDelete", "type": "otro"},
        )
        item_id = create_resp.json()["id"]
        resp = client.delete(f"/api/admin/utilities/{item_id}", headers=self.mod_headers)
        assert resp.status_code == 204

    def test_non_admin_cannot_create(self, client):
        resp = client.post("/api/admin/utilities",
            headers=self.user_headers,
            json={"name": "Hack", "type": "otro"},
        )
        assert resp.status_code == 403

    def test_non_admin_cannot_delete(self, client):
        create_resp = client.post("/api/admin/utilities",
            headers=self.mod_headers, json={"name": "X", "type": "otro"},
        )
        item_id = create_resp.json()["id"]
        resp = client.delete(f"/api/admin/utilities/{item_id}", headers=self.user_headers)
        assert resp.status_code == 403
