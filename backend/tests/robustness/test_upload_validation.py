"""Robustness tests for upload validation."""
import pytest
import io


class TestUploadValidation:
    """File upload endpoints must reject invalid files."""

    @pytest.mark.robustness
    def test_oversized_file_rejected(self, client, auth_headers):
        """Files larger than 5MB should be rejected."""
        headers = auth_headers(username="upload_test", email="uploadtest@test.com")

        # Create a contact first
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Upload Test",
            "phone": "3417777777",
        })
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]

        # Create a file larger than 5MB
        large_file = io.BytesIO(b"\x00" * (6 * 1024 * 1024))  # 6MB

        resp = client.post(
            f"/api/contacts/{cid}/photos",
            headers=headers,
            files={"file": ("large.jpg", large_file, "image/jpeg")},
        )
        assert resp.status_code in [400, 413, 422], \
            f"Oversized file should be rejected, got {resp.status_code}"

    @pytest.mark.robustness
    def test_fake_jpeg_rejected(self, client, auth_headers):
        """Text file with .jpg extension should be rejected."""
        headers = auth_headers(username="upload_test2", email="uploadtest2@test.com")

        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": "Fake JPEG Test",
            "phone": "3416666666",
        })
        cid = create_resp.json()["id"]

        # Text file pretending to be JPEG
        fake_jpeg = io.BytesIO(b"This is not a JPEG file, just plain text")

        resp = client.post(
            f"/api/contacts/{cid}/photos",
            headers=headers,
            files={"file": ("fake.jpg", fake_jpeg, "image/jpeg")},
        )
        assert resp.status_code in [400, 422], \
            f"Fake JPEG should be rejected, got {resp.status_code}"

    @pytest.mark.robustness
    def test_empty_file_rejected(self, client, auth_headers):
        """Empty file should be rejected."""
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
