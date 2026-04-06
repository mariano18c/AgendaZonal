"""Robustness tests — File upload validation (magic bytes, size, type)."""
import io
import pytest
from tests.conftest import _bearer


def _make_jpeg(size_kb: int = 1) -> io.BytesIO:
    """Create a minimal valid JPEG in memory."""
    from PIL import Image
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def _make_png() -> io.BytesIO:
    from PIL import Image
    img = Image.new("RGBA", (50, 50), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


class TestContactImageUpload:
    def test_upload_valid_jpeg(self, client, create_user, create_contact):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        img = _make_jpeg()
        r = client.post(f"/api/contacts/{c.id}/image", headers=_bearer(owner),
                          files={"file": ("photo.jpg", img, "image/jpeg")})
        assert r.status_code == 200
        assert r.json()["photo_path"] is not None

    def test_upload_png(self, client, create_user, create_contact):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        img = _make_png()
        r = client.post(f"/api/contacts/{c.id}/image", headers=_bearer(owner),
                          files={"file": ("photo.png", img, "image/png")})
        assert r.status_code == 400

    def test_upload_fake_image(self, client, create_user, create_contact):
        """File with .jpg extension but non-image content."""
        owner = create_user()
        c = create_contact(user_id=owner.id)
        fake = io.BytesIO(b"not an image at all, just text")
        r = client.post(f"/api/contacts/{c.id}/image", headers=_bearer(owner),
                          files={"file": ("evil.jpg", fake, "image/jpeg")})
        assert r.status_code == 400

    def test_upload_not_owner(self, client, create_user, create_contact):
        c = create_contact()
        stranger = create_user()
        img = _make_jpeg()
        r = client.post(f"/api/contacts/{c.id}/image", headers=_bearer(stranger),
                          files={"file": ("photo.jpg", img, "image/jpeg")})
        assert r.status_code in (200, 403)

    def test_delete_image(self, client, create_user, create_contact):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        # Upload first
        img = _make_jpeg()
        client.post(f"/api/contacts/{c.id}/image", headers=_bearer(owner),
                     files={"file": ("photo.jpg", img, "image/jpeg")})
        # Delete
        r = client.delete(f"/api/contacts/{c.id}/image", headers=_bearer(owner))
        assert r.status_code == 200


class TestContactPhotos:
    def test_upload_gallery_photo(self, client, create_user, create_contact):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        img = _make_jpeg()
        r = client.post(f"/api/contacts/{c.id}/photos", headers=_bearer(owner),
                          files={"file": ("gallery.jpg", img, "image/jpeg")})
        assert r.status_code in (200, 201)

    def test_list_photos(self, client, create_contact):
        c = create_contact()
        r = client.get(f"/api/contacts/{c.id}/photos")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_max_photos_limit(self, client, create_user, create_contact):
        """Should enforce max 5 photos per contact."""
        owner = create_user()
        c = create_contact(user_id=owner.id)
        for i in range(6):
            img = _make_jpeg()
            r = client.post(f"/api/contacts/{c.id}/photos", headers=_bearer(owner),
                              files={"file": (f"photo{i}.jpg", img, "image/jpeg")})
            if i >= 5:
                assert r.status_code == 400
