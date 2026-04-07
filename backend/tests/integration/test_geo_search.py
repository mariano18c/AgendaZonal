"""Integration tests for geo search endpoint. Merged from tests_ant."""
import pytest


class TestGeoSearch:
    """Test geo search endpoint."""

    @pytest.fixture(autouse=True)
    def setup_contacts(self, client, user_headers):
        """Create contacts at known geo locations for testing."""
        headers = user_headers
        # id=1: Rosario Centro (our search origin)
        client.post("/api/contacts", headers=headers, json={
            "name": "Plomero Centro", "phone": "3411111111",
            "city": "Rosario", "neighborhood": "Centro",
            "category_id": 1,
            "latitude": -32.95, "longitude": -60.65,
        })
        # id=2: Pichincha (~1.5km from center)
        client.post("/api/contacts", headers=headers, json={
            "name": "Plomero Pichincha", "phone": "3412222222",
            "city": "Rosario", "neighborhood": "Pichincha",
            "category_id": 1,
            "latitude": -32.94, "longitude": -60.64,
        })
        # id=3: Ibarlucea (~15km from center)
        client.post("/api/contacts", headers=headers, json={
            "name": "Plomero Ibarlucea", "phone": "3413333333",
            "city": "Ibarlucea", "neighborhood": "Centro",
            "category_id": 1,
            "latitude": -32.85, "longitude": -60.78,
        })
        # id=4: Buenos Aires (~280km — too far)
        client.post("/api/contacts", headers=headers, json={
            "name": "Plomero BA", "phone": "1114444444",
            "city": "Buenos Aires", "neighborhood": "Palermo",
            "category_id": 1,
            "latitude": -34.60, "longitude": -58.38,
        })
        # id=5: No coordinates
        client.post("/api/contacts", headers=headers, json={
            "name": "Plomero Sin Ubicacion", "phone": "3415555555",
            "city": "Rosario", "category_id": 1,
        })

    def test_geo_search_returns_nearby(self, client):
        """20km radius from Rosario Centro should return 3 contacts."""
        resp = client.get("/api/contacts/search", params={
            "lat": -32.95, "lon": -60.65, "radius_km": 20
        })
        assert resp.status_code == 200
        results = resp.json()["contacts"]
        names = [r["name"] for r in results]
        assert "Plomero Centro" in names
        assert "Plomero Pichincha" in names
        assert "Plomero Ibarlucea" in names
        assert "Plomero BA" not in names
        assert "Plomero Sin Ubicacion" not in names

    def test_geo_search_sorted_by_distance(self, client):
        """Results sorted by distance, closest first."""
        resp = client.get("/api/contacts/search", params={
            "lat": -32.95, "lon": -60.65, "radius_km": 20
        })
        results = resp.json()["contacts"]
        distances = [r["distance_km"] for r in results]
        assert distances == sorted(distances)
        assert distances[0] == pytest.approx(0.0, abs=0.1)

    def test_geo_search_includes_distance_km(self, client):
        """Each result includes distance_km field."""
        resp = client.get("/api/contacts/search", params={
            "lat": -32.95, "lon": -60.65, "radius_km": 20
        })
        for result in resp.json()["contacts"]:
            assert "distance_km" in result
            assert isinstance(result["distance_km"], (int, float))

    def test_geo_search_small_radius(self, client):
        """5km radius excludes Ibarlucea (~15km)."""
        resp = client.get("/api/contacts/search", params={
            "lat": -32.95, "lon": -60.65, "radius_km": 5
        })
        results = resp.json()["contacts"]
        names = [r["name"] for r in results]
        assert "Plomero Centro" in names
        assert "Plomero Pichincha" in names
        assert "Plomero Ibarlucea" not in names

    def test_geo_search_with_text(self, client):
        """Geo search combined with text query."""
        resp = client.get("/api/contacts/search", params={
            "q": "Pichincha",
            "lat": -32.95, "lon": -60.65, "radius_km": 20
        })
        results = resp.json()["contacts"]
        assert len(results) >= 1
        assert any("Pichincha" in r["name"] for r in results)

    def test_geo_search_with_category(self, client):
        """Geo search combined with category filter."""
        resp = client.get("/api/contacts/search", params={
            "category_id": 1,
            "lat": -32.95, "lon": -60.65, "radius_km": 20
        })
        assert resp.status_code == 200
        results = resp.json()["contacts"]
        assert len(results) >= 1
        assert all(r["category_id"] == 1 for r in results)

    def test_search_without_geo_still_works(self, client):
        """Text search without geo — backward compatible."""
        resp = client.get("/api/contacts/search", params={"q": "Plomero"})
        assert resp.status_code == 200
        results = resp.json()["contacts"]
        assert len(results) >= 5
        names = {r["name"] for r in results}
        assert "Plomero Centro" in names

    def test_search_no_filters_returns_400(self, client):
        """No filters at all → 400."""
        resp = client.get("/api/contacts/search")
        assert resp.status_code == 400

    def test_geo_search_invalid_coords_returns_400(self, client):
        """Invalid coordinates → 400."""
        resp = client.get("/api/contacts/search", params={
            "lat": -91, "lon": -60.65, "radius_km": 10
        })
        assert resp.status_code == 400

    def test_geo_search_only_lat_uses_text(self, client):
        """lat without lon → geo not activated, text search."""
        resp = client.get("/api/contacts/search", params={
            "lat": -32.95, "q": "Plomero"
        })
        assert resp.status_code == 200
        results = resp.json()["contacts"]
        assert len(results) >= 5
        names = {r["name"] for r in results}
        assert "Plomero Centro" in names
        for r in results:
            assert r.get("distance_km") is None
