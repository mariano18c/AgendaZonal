import pytest
import io
from PIL import Image


class TestImageUpload:

    def _create_jpeg_bytes(self, width=100, height=100):
        img = Image.new("RGB", (width, height), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        return buf

    @pytest.fixture
    def image_setup(self, client, auth_headers):
        """Create user and contact, return (headers, contact_id)."""
        headers = auth_headers(username="imguser", email="img@test.com")
        resp = client.post("/api/contacts", headers=headers, json={
            "name": "Con Imagen",
            "phone": "1234567",
        })
        return headers, resp.json()["id"]

    @pytest.mark.integration
    def test_upload_imagen_valida(self, client, image_setup):
        headers, contact_id = image_setup
        jpeg = self._create_jpeg_bytes()

        resp = client.post(
            f"/api/contacts/{contact_id}/image",
            headers=headers,
            files={"file": ("test.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 200
        assert resp.json()["photo_path"] is not None

    @pytest.mark.integration
    def test_upload_archivo_no_jpeg(self, client, image_setup):
        headers, contact_id = image_setup
        png_buf = io.BytesIO()
        Image.new("RGB", (100, 100)).save(png_buf, format="PNG")
        png_buf.seek(0)

        resp = client.post(
            f"/api/contacts/{contact_id}/image",
            headers=headers,
            files={"file": ("test.png", png_buf, "image/png")},
        )
        assert resp.status_code == 400

    @pytest.mark.integration
    def test_upload_sin_autenticacion(self, client, image_setup):
        _, contact_id = image_setup
        # Clear cookies to ensure no auth is sent
        client.cookies.clear()
        jpeg = self._create_jpeg_bytes()
        resp = client.post(
            f"/api/contacts/{contact_id}/image",
            files={"file": ("test.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 401

    @pytest.mark.integration
    def test_eliminar_imagen(self, client, image_setup):
        headers, contact_id = image_setup
        jpeg = self._create_jpeg_bytes()

        client.post(
            f"/api/contacts/{contact_id}/image",
            headers=headers,
            files={"file": ("test.jpg", jpeg, "image/jpeg")},
        )

        resp = client.delete(f"/api/contacts/{contact_id}/image", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["photo_path"] is None
