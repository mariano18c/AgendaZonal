import sys
import json
import sqlite3
from pathlib import Path

# Agregar el directorio de scripts al path para importar ocr_engine
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

from ocr_engine import process_single_image

DB_PATH = BASE_DIR / "database" / "agenda.db"
IMAGES_DIR = BASE_DIR.parent / "fuente_datos" / "importados_ok" / "imagenes"

def get_category_name(cursor, cat_id):
    cursor.execute("SELECT name FROM categories WHERE id = ?", (cat_id,))
    row = cursor.fetchone()
    return row[0] if row else f"ID {cat_id}"

def validate_ocr():
    if not IMAGES_DIR.exists():
        print(f"La carpeta de imágenes no existe: {IMAGES_DIR}")
        return

    image_paths = list(IMAGES_DIR.glob("*.jpg")) + list(IMAGES_DIR.glob("*.jpeg")) + list(IMAGES_DIR.glob("*.png"))
    
    if not image_paths:
        print("No se encontraron imágenes para validar.")
        return

    print(f"Iniciando validación de {len(image_paths)} imágenes (SIN MODIFICAR LA BD)...\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    results = []
    
    for filepath in image_paths:
        print(f"Procesando: {filepath.name}")
        ocr_result = process_single_image(filepath)
        
        if not ocr_result:
            results.append({
                "file": filepath.name,
                "status": "No OCR Data",
                "details": "No se pudo extraer información útil."
            })
            continue

        phones = ocr_result.get("phones", [])
        ocr_name = ocr_result.get("name")
        ocr_cat_id = ocr_result.get("category_id")
        
        db_match = None
        match_by = None
        
        # Intentar buscar por teléfono primero
        if phones:
            primary_phone = phones[0]
            cursor.execute("SELECT id, name, phone, category_id, description FROM contacts WHERE phone = ?", (primary_phone,))
            db_match = cursor.fetchone()
            if db_match:
                match_by = "Phone"
        
        # Si no hay por teléfono, intentar por nombre aproximado (solo como referencia)
        if not db_match and ocr_name:
            # Búsqueda simple
            cursor.execute("SELECT id, name, phone, category_id, description FROM contacts WHERE name LIKE ?", (f"%{ocr_name}%",))
            db_match = cursor.fetchone()
            if db_match:
                match_by = "Name"
                
        if db_match:
            db_id, db_name, db_phone, db_cat_id, db_desc = db_match
            
            ocr_cat_name = get_category_name(cursor, ocr_cat_id)
            db_cat_name = get_category_name(cursor, db_cat_id)
            
            comparison = {
                "file": filepath.name,
                "status": "Matched",
                "match_by": match_by,
                "ocr_data": {
                    "name": ocr_name,
                    "phone": phones[0] if phones else None,
                    "category": f"{ocr_cat_name} ({ocr_cat_id})",
                    "confidence": ocr_result.get("confidence")
                },
                "db_data": {
                    "name": db_name,
                    "phone": db_phone,
                    "category": f"{db_cat_name} ({db_cat_id})",
                    "id": db_id
                },
                "matches": {
                    "name": ocr_name and ocr_name.lower() in db_name.lower() or db_name.lower() in (ocr_name or "").lower(),
                    "category": ocr_cat_id == db_cat_id,
                    "phone": (phones[0] if phones else None) == db_phone
                }
            }
            results.append(comparison)
        else:
            ocr_cat_name = get_category_name(cursor, ocr_cat_id)
            results.append({
                "file": filepath.name,
                "status": "Not Found in DB",
                "ocr_data": {
                    "name": ocr_name,
                    "phone": phones[0] if phones else None,
                    "category": f"{ocr_cat_name} ({ocr_cat_id})",
                    "confidence": ocr_result.get("confidence")
                }
            })

    conn.close()
    
    # Escribir reporte
    report_file = BASE_DIR / "scripts" / "ocr_validation_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\nValidación completada. Reporte guardado en: {report_file.name}")
    
    # Resumen rápido en consola
    matched = sum(1 for r in results if r["status"] == "Matched")
    not_found = sum(1 for r in results if r["status"] == "Not Found in DB")
    no_data = sum(1 for r in results if r["status"] == "No OCR Data")
    
    print("\n--- Resumen ---")
    print(f"Total procesadas: {len(image_paths)}")
    print(f"Encontradas en BD: {matched}")
    print(f"No encontradas en BD: {not_found}")
    print(f"Sin datos OCR: {no_data}")

if __name__ == "__main__":
    # Asegurar utf-8 stdout para Windows
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    validate_ocr()
