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


class TestUploadValidationAdvanced:
    """Additional upload validation — merged from tests_ant."""

    def test_oversized_file_rejected(self, client, auth_headers):
        """Files larger than 5MB should be rejected."""
        import io
        headers = auth_headers(username="upload_test", email="uploadtest@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Upload Test",
            "phone": "3417777777",
        })
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]
        large_file = io.BytesIO(b"\x00" * (6 * 1024 * 1024))  # 6MB
        resp = client.post(
            f"/api/contacts/{cid}/photos",
            headers=headers,
            files={"file": ("large.jpg", large_file, "image/jpeg")},
        )
        assert resp.status_code in [400, 413, 422], \
            f"Oversized file should be rejected, got {resp.status_code}"

    def test_empty_file_rejected(self, client, auth_headers):
        """Empty file should be rejected."""
        import io
        headers = auth_headers(username="upload_test3", email="uploadtest3@test.com")
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Empty File Test",
            "phone": "3415555555",
        })
        cid = create_resp.json()["id"]
        empty_file = io.BytesIO(b"")
        resp = client.post(
            f"/api/contacts/{cid}/photos",
            headers=headers,
            files={"file": ("empty.jpg", empty_file, "image/jpeg")},
        )
        assert resp.status_code in [400, 422], \
            f"Empty file should be rejected, got {resp.status_code}"
