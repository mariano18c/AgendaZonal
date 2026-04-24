import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "agenda.db"

NEW_CATEGORIES = [
    (142, "Cerrajería", "key", "Servicios de cerrajería"),
    (143, "Bicicletería", "bike", "Reparación y venta de bicicletas"),
]

def add_new_categories():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for code, name, icon, desc in NEW_CATEGORIES:
        cursor.execute("SELECT id FROM categories WHERE name = ?", (name,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO categories (code, name, icon, description)
                VALUES (?, ?, ?, ?)
            """, (code, name, icon, desc))
            print(f"Added category: {name}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_new_categories()
