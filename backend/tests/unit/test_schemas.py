import pytest
from pydantic import ValidationError
from app.schemas.contact import ContactCreate, ContactUpdate
from app.schemas.auth import RegisterRequest


class TestContactCreateSchema:

    @pytest.mark.unit
    def test_contacto_minimo_valido(self):
        contact = ContactCreate(name="Juan Perez", phone="341-1234567")
        assert contact.name == "Juan Perez"

    @pytest.mark.unit
    def test_contacto_completo_valido(self):
        contact = ContactCreate(
            name="Juan Perez",
            phone="341-1234567",
            email="juan@test.com",
            city="Rosario",
            category_id=1,
            website="https://ejemplo.com",
            latitude=-32.95,
            longitude=-60.63,
        )
        assert contact.email == "juan@test.com"

    @pytest.mark.unit
    def test_nombre_muy_corto(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="A", phone="341-1234567")

    @pytest.mark.unit
    def test_nombre_muy_largo(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="A" * 101, phone="341-1234567")

    @pytest.mark.unit
    def test_telefono_con_letras(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Juan", phone="abc123")

    @pytest.mark.unit
    def test_telefono_valido_con_guiones(self):
        contact = ContactCreate(name="Juan", phone="(0341) 123-4567")
        assert contact.phone == "(0341) 123-4567"

    @pytest.mark.unit
    def test_email_invalido(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Juan", phone="341-1234567", email="noesemail")

    @pytest.mark.unit
    def test_website_sin_http(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Juan", phone="341-1234567", website="ejemplo.com")

    @pytest.mark.unit
    def test_website_con_https_valido(self):
        contact = ContactCreate(name="Juan", phone="341-1234567", website="https://ejemplo.com")
        assert contact.website == "https://ejemplo.com"

    @pytest.mark.unit
    def test_latitud_fuera_de_rango(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Juan", phone="341-1234567", latitude=91.0)

    @pytest.mark.unit
    def test_longitud_fuera_de_rango(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="Juan", phone="341-1234567", longitude=181.0)

    @pytest.mark.unit
    def test_coordenadas_en_limites(self):
        contact = ContactCreate(name="Juan", phone="341-1234567", latitude=90.0, longitude=-180.0)
        assert contact.latitude == 90.0


class TestContactUpdateSchema:

    @pytest.mark.unit
    def test_update_parcial(self):
        contact = ContactUpdate(name="Nuevo nombre")
        assert contact.name == "Nuevo nombre"
        assert contact.phone is None

    @pytest.mark.unit
    def test_update_vacio_permitido(self):
        contact = ContactUpdate()
        assert contact.name is None


class TestRegisterRequestSchema:

    @pytest.mark.unit
    def test_registro_valido(self):
        reg = RegisterRequest(
            username="testuser",
            email="test@test.com",
            phone_area_code="0341",
            phone_number="1234567",
            password="password123",
        )
        assert reg.username == "testuser"

    @pytest.mark.unit
    def test_password_muy_corto(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="testuser",
                email="test@test.com",
                phone_area_code="0341",
                phone_number="1234567",
                password="short",
            )
