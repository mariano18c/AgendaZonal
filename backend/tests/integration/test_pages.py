"""Integration tests — HTML pages, health, slug redirect, static."""
import pytest


class TestHealthCheck:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"


class TestHTMLPages:
    """Verify that all pages return 200 and serve HTML content."""

    @pytest.mark.parametrize("path", [
        "/",
        "/search",
        "/login",
        "/register",
        "/add",
    ])
    def test_public_pages(self, client, path):
        r = client.get(path)
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    @pytest.mark.parametrize("path", [
        "/edit",
        "/dashboard",
        "/history",
        "/pending",
        "/profile",
    ])
    def test_protected_pages_return_html(self, client, path):
        """Protected pages still serve HTML (auth checked client-side)."""
        r = client.get(path)
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    @pytest.mark.parametrize("path", [
        "/admin/reviews",
        "/admin/reports",
        "/admin/analytics",
        "/admin/utilities",
        "/admin/users",
    ])
    def test_admin_pages_return_html(self, client, path):
        r = client.get(path)
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")


class TestSlugRedirect:
    def test_slug_redirect(self, client, create_contact):
        c = create_contact(slug="ferreteria-juan")
        r = client.get("/c/ferreteria-juan", follow_redirects=False)
        assert r.status_code in (301, 302, 307)
        assert f"id={c.id}" in r.headers.get("location", "")

    def test_slug_not_found(self, client):
        r = client.get("/c/nonexistent-slug")
        assert r.status_code == 404


class TestCategories:
    def test_list_categories(self, client):
        r = client.get("/api/categories")
        assert r.status_code == 200
        cats = r.json()
        assert len(cats) == 36
        codes = [c["code"] for c in cats]
        assert 100 in codes
        assert 999 in codes


class TestOfflinePage:
    def test_offline_page(self, client):
        r = client.get("/offline.html")
        assert r.status_code == 200


class TestPublicUsersList:
    def test_public_users(self, client, create_user):
        create_user()
        r = client.get("/api/public/users")
        assert r.status_code == 200
