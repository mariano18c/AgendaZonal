"""Image service — upload, resize, and delete contact images."""
from pathlib import Path
from PIL import Image

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "images"
MAX_IMAGE_SIZE = (1024, 1024)


def resize_image(image: Image.Image, max_size: tuple = MAX_IMAGE_SIZE) -> Image.Image:
    """Resize image while maintaining aspect ratio."""
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    return image


def save_image(contact_id: int, content: bytes) -> str:
    """Save JPEG content to disk. Returns the photo_path."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"contact_{contact_id}.jpg"
    filepath = UPLOAD_DIR / filename

    image = Image.open(__import__("io").BytesIO(content))
    if image.mode != 'RGB':
        image = image.convert('RGB')
    if image.width > MAX_IMAGE_SIZE[0] or image.height > MAX_IMAGE_SIZE[1]:
        image = resize_image(image)
    image.save(filepath, 'JPEG', quality=85)
    return f"/uploads/images/{filename}"


def delete_image(contact_id: int) -> bool:
    """Delete image file for a contact. Returns True if file was deleted."""
    filename = f"contact_{contact_id}.jpg"
    filepath = UPLOAD_DIR / filename
    if filepath.exists():
        __import__("os").remove(filepath)
        return True
    return False
