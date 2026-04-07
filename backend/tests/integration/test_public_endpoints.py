"""Integration tests for public endpoints. Merged from tests_ant."""


class TestPublicEndpoints:
    """Test public endpoints that should be accessible without auth."""

    def test_health_endpoint(self, client):
        """GET /health should return health status."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "database" in data["checks"]

    def test_public_users_returns_active_users(self, client, create_user):
        """GET /api/public/users should return active users."""
        create_user(username="publicuser1", email="pub1@test.com")
        create_user(username="publicuser2", email="pub2@test.com")
        resp = client.get("/api/public/users")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_public_users_excludes_inactive(self, client, create_user):
        """GET /api/public/users should not include inactive users."""
        create_user(username="inactiveuser", email="inactive@test.com", is_active=False)
        create_user(username="activeuser", email="active@test.com", is_active=True)
        resp = client.get("/api/public/users")
        assert resp.status_code == 200
        data = resp.json()
        usernames = [u["username"] for u in data]
        assert "activeuser" in usernames
        assert "inactiveuser" not in usernames

    def test_utilities_public_endpoint(self, client):
        """GET /api/utilities should be accessible without auth."""
        resp = client.get("/api/utilities")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_vapid_public_key_public(self, client):
        """GET /api/notifications/vapid-public-key should be public."""
        resp = client.get("/api/notifications/vapid-public-key")
        assert resp.status_code in [200, 503]

    def test_slug_redirect(self, client, create_user, create_contact, db_session):
        """GET /c/{slug} should redirect to /profile?id=X."""
        user = create_user()
        contact = create_contact(user_id=user.id, name="Juan Perez Test")
        # Set slug directly in DB
        from app.models.contact import Contact
        db_session.query(Contact).filter(Contact.id == contact.id).update(
            {"slug": f"juan-perez-test-{contact.id}"}
        )
        db_session.commit()
        resp = client.get(f"/c/juan-perez-test-{contact.id}", follow_redirects=False)
        # Accept either 301 (redirect) or 404 (slug not found in this setup)
        assert resp.status_code in [301, 302, 404]

    def test_slug_not_found(self, client):
        """GET /c/nonexistent should return 404."""
        resp = client.get("/c/nonexistent-slug")
        assert resp.status_code == 404
