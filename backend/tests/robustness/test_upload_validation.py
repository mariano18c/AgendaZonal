"""Robustness tests for upload validation.

Adapted from tests_ant/robustness/test_upload_validation.py — uses current conftest fixtures.
Covers:
- Oversized file rejected (>5MB)
- Fake JPEG rejected (text file with .jpg extension)
- Empty file rejected
"""
import io
import uuid
import pytest


def _uid():
    return uuid.uuid4().hex[:8]


class TestUploadValidation:

    @pytest.mark.robustness
    def test_oversized_file_rejected(self, client, auth_headers):
        """Files larger than 5MB should be rejected."""
        headers = auth_headers(username=f"upload_test_{_uid()}", email=f"uploadtest_{_uid()}@test.com")

        # Create a contact first
        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Upload Test {_uid()}",
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
        headers = auth_headers(username=f"upload_test2_{_uid()}", email=f"uploadtest2_{_uid()}@test.com")

        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Fake JPEG Test {_uid()}",
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
        headers = auth_headers(username=f"upload_test3_{_uid()}", email=f"uploadtest3_{_uid()}@test.com")

        create_resp = client.post("/api/contacts", headers=headers, json={
            "name": f"Empty File Test {_uid()}",
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
