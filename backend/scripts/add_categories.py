import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "agenda.db"

NEW_CATEGORIES = [
    (135, "Cerrajería", "key", "Servicios de cerrajería"),
    (136, "Bicicletería", "bike", "Reparación y venta de bicicletas"),
    (137, "Remis/Taxi", "car", "Servicios de transporte"),
    (138, "Modista/Costura", "scissors", "Arreglo de ropa y costura"),
    (139, "Vivero", "flower", "Venta de plantas y jardín"),
    (140, "Arquitectura/Diseño", "home", "Estudios de arquitectura y diseño"),
    (141, "Gimnasio/Deporte", "activity", "Fitness y actividades físicas"),
]

def add_new_categories():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for code, name, icon, desc in NEW_CATEGORIES:
        cursor.execute("SELECT id FROM categories WHERE code = ?", (code,))
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
