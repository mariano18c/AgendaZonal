import sqlite3
import sys
from pathlib import Path

# Configurar encoding para consola
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "agenda.db"

def list_categories():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM categories ORDER BY id")
    cats = cursor.fetchall()
    conn.close()
    return cats

def fetch_others():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description FROM contacts WHERE category_id = 26")
    others = cursor.fetchall()
    conn.close()
    return others

if __name__ == "__main__":
    print("--- CATEGORIAS ---")
    for id, name in list_categories():
        print(f"{id}: {name}")
    
    print("\n--- CONTACTOS EN 'OTRO' (Limit 100) ---")
    others = fetch_others()
    for id, name, desc in others[:100]:
        try:
            print(f"ID: {id} | Name: {name} | Desc: {desc or ''}")
        except:
            # Fallback para caracteres problemáticos
            print(f"ID: {id} | Name: [Enc Error] | Desc: {desc or ''}")
    
    print(f"\nTotal en 'Otro': {len(others)}")
