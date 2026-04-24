import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "agenda.db"

MAPPING = {
    # Categoría ID: [Keywords]
    1: ["plomero", "plomeria", "gasista"], # 1 y 2 estan medio juntos
    2: ["gasista"],
    3: ["electricista", "electricidad"],
    4: ["peluqueria", "barberia", "coiffeur", "peinados"],
    5: ["albañil", "construccion", "reformas"],
    8: ["supermercado", "super"],
    9: ["carniceria", "carnes", "granja"],
    10: ["verduleria", "fruteria"],
    11: ["panaderia", "facturas", "panificadora"],
    13: ["farmacia"],
    15: ["bar", "cafeteria", "cafe"],
    16: ["restaurant", "rotiseria", "comidas", "pizzeria", "hamburgueseria"],
    19: ["veterinaria", "mascotas", "canino", "felino"],
    20: ["ferreteria"],
    21: ["kiosco", "almacen", "despensa"],
    24: ["cuidado", "niñera", "geriatrico", "adultos mayores"],
    25: ["inmobiliaria", "propiedades", "alquiler"],
    27: ["comuna", "municipalidad", "registro civil", "policia", "comisaria", "bomberos", "emergencias", "gobierno", "municipio", "concejo"],
    28: ["jardin", "escuela", "colegio", "maternal", "apoyo escolar", "docente"],
    30: ["flete", "mudanza", "cadete", "cadeteria", "comisionista"],
    36: ["sanatorio", "hospital", "samco", "clinica", "medico", "odontologo", "odontologia", "kinesiologo", "kinesiologia", "consultorio", "ambulancia"],
    37: ["taller", "reparacion", "reparaciones", "service", "aire acondicionado"],
    38: ["mecanico", "mecanica", "repuestos", "auto", "smata"]
}

def auto_moderate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    cursor.execute("SELECT id, name, description FROM contacts WHERE category_id = 26")
    others = cursor.fetchall()
    
    updated = 0
    total = len(others)
    
    print(f"Iniciando moderación de {total} contactos en 'Otro'...")
    
    for contact_id, name, desc in others:
        text = f"{name} {desc or ''}".lower()
        
        found_cat = None
        for cat_id, keywords in MAPPING.items():
            for kw in keywords:
                if kw in text:
                    found_cat = cat_id
                    break
            if found_cat: break
        
        if found_cat:
            cursor.execute("UPDATE contacts SET category_id = ?, updated_at = datetime('now') WHERE id = ?", (found_cat, contact_id))
            updated += 1
            # print(f"Update: {name} -> Cat {found_cat}")

    conn.commit()
    conn.close()
    print(f"Moderación completada: {updated} de {total} contactos re-categorizados.")

if __name__ == "__main__":
    auto_moderate()
