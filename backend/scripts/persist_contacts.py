import json
import sqlite3
from pathlib import Path

# Configuración
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "agenda.db"
INPUT_FILE = BASE_DIR / "scripts" / "contacts_enriched.json"

def persist_contacts():
    if not INPUT_FILE.exists():
        print(f"Error: No se encontró {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        contacts = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Asegurar modo WAL para performance en RPi 5
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    print(f"Iniciando persistencia en {DB_PATH.name}...")
    
    inserted = 0
    skipped = 0
    
    for c in contacts:
        name = c["name"]
        phone = c["phones"][0] if c["phones"] else None
        category_id = c["category_id"]
        
        # Verificar duplicado por teléfono
        if phone:
            cursor.execute("SELECT id FROM contacts WHERE phone = ?", (phone,))
            if cursor.fetchone():
                skipped += 1
                continue
        
        # Insertar contacto
        try:
            cursor.execute("""
                INSERT INTO contacts (name, phone, category_id, status, is_verified, verification_level, created_at, updated_at)
                VALUES (?, ?, ?, 'active', 0, 0, datetime('now'), datetime('now'))
            """, (name, phone, category_id))
            inserted += 1
        except Exception as e:
            print(f"Error insertando {name}: {e}")
            skipped += 1

    conn.commit()
    conn.close()
    
    print("\n--- Resumen de Persistencia ---")
    print(f"  Insertados: {inserted}")
    print(f"  Omitidos (duplicados/error): {skipped}")
    print(f"  Total procesados: {len(contacts)}")

if __name__ == "__main__":
    persist_contacts()
