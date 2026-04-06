"""Unit tests — Image service (resize, save, delete)."""
import io
import pytest
from pathlib import Path
from PIL import Image
from app.services import image_service


def _make_jpeg() -> bytes:
    img = Image.new("RGB", (2000, 2000), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestImageService:
    def test_resize_image(self):
        img = Image.new("RGB", (2000, 2000), color="blue")
        resized = image_service.resize_image(img, (100, 100))
        assert resized.width <= 100
        assert resized.height <= 100

    def test_save_image_logic(self, db_session):
        content = _make_jpeg()
        photo_path = image_service.save_image(999, content)
        
        assert photo_path == "/uploads/images/contact_999.jpg"
        
        # Check if file exists on disk
        full_path = Path(__file__).resolve().parent.parent.parent / "uploads" / "images" / "contact_999.jpg"
        assert full_path.exists()
        
        # Cleanup
        image_service.delete_image(999)
        assert not full_path.exists()

    def test_delete_nonexistent_image(self):
        result = image_service.delete_image(88888)
        assert result is False

    def test_convert_to_rgb(self, db_session):
        """Save a RGBA image and ensure it's converted to RGB."""
        img = Image.new("RGBA", (100, 100), color="green")
        buf = io.BytesIO()
        img.save(buf, format="PNG") # Use PNG to support RGBA
        content = buf.getvalue()
        
        # Even if the source is PNG, save_image expects bytes and will use Image.open
        photo_path = image_service.save_image(777, content)
        
        # Check file
        full_path = Path(__file__).resolve().parent.parent.parent / "uploads" / "images" / "contact_777.jpg"
        with Image.open(full_path) as saved_img:
            assert saved_img.mode == "RGB"
        
        # Cleanup
        image_service.delete_image(777)
