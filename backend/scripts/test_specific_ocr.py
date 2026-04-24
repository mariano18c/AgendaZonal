import sys
from pathlib import Path

# Agregar el directorio de scripts al path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from ocr_engine import ocr_image, extract_phones

IMAGES_DIR = BASE_DIR.parent.parent / "fuente_datos" / "importados_ok" / "imagenes"

test_images = [
    "IMG-20250426-WA0841.jpg", # Plomero pero sin telefono detectado
    "IMG-20260416-WA0008.jpg", # Veterinaria pero sin telefono detectado
    "IMG-20250503-WA0385.jpg", # Detecto telefono pero no estaba en DB
]

def analyze_images():
    for img_name in test_images:
        img_path = IMAGES_DIR / img_name
        if not img_path.exists():
            print(f"No se encontro {img_name}")
            continue
            
        print("="*50)
        print(f"Analizando: {img_name}")
        print("-" * 50)
        raw_text = ocr_image(img_path)
        print("--- RAW OCR TEXT ---")
        print(raw_text)
        print("--- TELÉFONOS DETECTADOS ---")
        phones = extract_phones(raw_text)
        print(phones)
        print("="*50 + "\n")

if __name__ == "__main__":
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    analyze_images()
