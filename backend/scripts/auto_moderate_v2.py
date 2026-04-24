import sqlite3
import sys
from pathlib import Path

# Configurar encoding para consola si es necesario
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "agenda.db"

MAPPING = {
    1: ["plomero", "plomeria"],
    2: ["gasista"],
    3: ["electricista", "electricidad"],
    4: ["peluqueria", "barberia", "estetica"],
    9: ["carniceria", "carnes", "granja"],
    10: ["verduleria", "fruteria"],
    11: ["panaderia", "reposteria", "tortas", "facturas"],
    13: ["farmacia"],
    19: ["veterinaria", "vete", "mascotas"],
    20: ["ferreteria", "materiales para la construccion"],
    21: ["kiosco", "almacen", "despensa"],
    25: ["inmobiliaria", "propiedades", "alquiler"],
    27: ["comuna", "municipalidad", "registro civil", "policia", "comisaria", "bomberos", "emergencias", "gobierno", "municipio", "concejo", "violencia de genero", "144", "911"],
    28: ["jardin", "escuela", "colegio", "maternal", "apoyo escolar", "clases", "taller de"],
    30: ["flete", "mudanza", "cadete", "cadeteria", "comisionista"],
    36: ["sanatorio", "hospital", "samco", "clinica", "medico", "odontologo", "odontologia", "kinesiologo", "kinesiologia", "consultorio", "dentista", "dispensario", "ambulancia"],
    37: ["taller", "reparacion", "service", "aire acondicionado"],
    38: ["mecanico", "repuestos", "auto", "smata"],
    39: ["remis", "taxi", "chofer"],
    40: ["modista", "costura", "ropa", "arreglos"],
    41: ["vivero", "plantas", "jardin"],
    42: ["arquitectura", "arquitecto", "estudio"],
    43: ["gym", "gimnasio", "fitness", "entrenamiento"],
    44: ["cerrajero", "cerrajeria"],
    45: ["bicicletero", "bicicleteria", "bicicleta", "bici"]
}

def auto_moderate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Solo procesar los que siguen en "Otro" (cat id 26)
    cursor.execute("SELECT id, name, description FROM contacts WHERE category_id = 26")
    others = cursor.fetchall()
    
    updated = 0
    total = len(others)
    
    print(f"Iniciando moderación mejorada de {total} contactos en 'Otro'...")
    
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
            try:
                cursor.execute("UPDATE contacts SET category_id = ?, updated_at = datetime('now') WHERE id = ?", (found_cat, contact_id))
                updated += 1
                # print(f"Update: {name[:30]}... -> Cat {found_cat}")
            except Exception as e:
                print(f"Error actualizando {contact_id}: {e}")

    conn.commit()
    conn.close()
    print(f"Moderación completada: {updated} de {total} contactos re-categorizados.")

if __name__ == "__main__":
    auto_moderate()
