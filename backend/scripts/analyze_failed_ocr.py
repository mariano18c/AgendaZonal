import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
from ocr_engine import ocr_image, extract_phones

IMAGES_DIR = BASE_DIR.parent.parent / "fuente_datos" / "importados_ok" / "imagenes"
REPORT_PATH = BASE_DIR / "ocr_validation_report.json"

def analyze_failures():
    if not REPORT_PATH.exists():
        print("No se encontró el reporte de validación.")
        return

    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)

    failed_cases = [r for r in report if r["status"] == "Not Found in DB"]
    
    analysis = {
        "no_phone_detected": [],
        "phone_detected_not_in_db": [],
        "almost_empty_ocr": []
    }

    print(f"Analizando {len(failed_cases)} casos que no hicieron Match...\n")

    for case in failed_cases:
        img_name = case["file"]
        img_path = IMAGES_DIR / img_name
        
        if not img_path.exists():
            continue
            
        raw_text = ocr_image(img_path)
        phones = extract_phones(raw_text)
        
        if len(raw_text.strip()) < 10:
            analysis["almost_empty_ocr"].append(img_name)
        elif not phones:
            analysis["no_phone_detected"].append(img_name)
        else:
            analysis["phone_detected_not_in_db"].append({"file": img_name, "phones": phones})

    print("=== RESULTADOS DEL ANÁLISIS PROFUNDO ===")
    print(f"1. Imágenes con poco/nada de texto extraído: {len(analysis['almost_empty_ocr'])}")
    # for f in analysis['almost_empty_ocr']: print(f"   - {f}")
    
    print(f"\n2. Imágenes con texto pero SIN TELÉFONO detectado: {len(analysis['no_phone_detected'])}")
    # for f in analysis['no_phone_detected']: print(f"   - {f}")
    
    print(f"\n3. Imágenes con teléfono detectado, PERO el teléfono no existe en la BD: {len(analysis['phone_detected_not_in_db'])}")
    for item in analysis['phone_detected_not_in_db']:
        print(f"   - {item['file']} (Teléfonos: {item['phones']})")

if __name__ == "__main__":
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    analyze_failures()
