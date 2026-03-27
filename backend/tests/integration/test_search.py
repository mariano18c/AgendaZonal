import pytest


class TestBusqueda:

    @pytest.fixture(autouse=True)
    def setup_contacts(self, client, auth_headers):
        headers = auth_headers(username="searchuser", email="search@test.com")
        contacts = [
            {"name": "Juan Plomero", "phone": "1111111", "city": "Rosario", "category_id": 1},
            {"name": "Maria Gasista", "phone": "2222222", "city": "Buenos Aires", "category_id": 2},
            {"name": "Carlos Electricista", "phone": "3333333", "city": "Rosario", "category_id": 3},
        ]
        for c in contacts:
            client.post("/api/contacts", headers=headers, json=c)

    @pytest.mark.integration
    def test_busqueda_por_nombre(self, client):
        resp = client.get("/api/contacts/search?q=Juan")
        assert resp.status_code == 200
        assert any("Juan" in c["name"] for c in resp.json())

    @pytest.mark.integration
    def test_busqueda_por_ciudad(self, client):
        resp = client.get("/api/contacts/search?q=Rosario")
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 2

    @pytest.mark.integration
    def test_busqueda_por_categoria(self, client):
        resp = client.get("/api/contacts/search?category_id=1")
        assert resp.status_code == 200
        for c in resp.json():
            assert c["category_id"] == 1

    @pytest.mark.integration
    def test_busqueda_sin_parametros(self, client):
        resp = client.get("/api/contacts/search")
        assert resp.status_code == 400

    @pytest.mark.integration
    def test_busqueda_sin_resultados(self, client):
        resp = client.get("/api/contacts/search?q=XYZNOEXISTE")
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    @pytest.mark.integration
    def test_busqueda_case_insensitive(self, client):
        resp = client.get("/api/contacts/search?q=juan")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestCategorias:

    @pytest.mark.integration
    def test_listar_categorias(self, client):
        resp = client.get("/api/categories")
        assert resp.status_code == 200
        cats = resp.json()
        assert len(cats) >= 4

    @pytest.mark.integration
    def test_categorias_ordenadas_por_nombre(self, client):
        resp = client.get("/api/categories")
        cats = resp.json()
        names = [c["name"] for c in cats]
        assert names == sorted(names)
