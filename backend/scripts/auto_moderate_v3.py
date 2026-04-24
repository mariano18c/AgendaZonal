import sqlite3
import re
import sys
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "agenda.db"

MAPPING = {
    1: ["plomero", "plomeria"],
    2: ["gasista", "gas"],
    3: ["electricista", "electricidad", "electrica"],
    4: ["peluqueria", "barberia", "estetica", "manicura", "nails"],
    9: ["carniceria", "carnes", "granja", "frigorifico"],
    10: ["verduleria", "fruteria", "huerta"],
    11: ["panaderia", "reposteria", "tortas", "facturas", "pasteleria", "confiteria"],
    12: ["ropa", "tienda", "indumentaria", "shopp"],
    13: ["farmacia"],
    19: ["veterinaria", "vete", "mascotas", "canino", "felino"],
    20: ["ferreteria", "materiales para la construccion", "maderas", "maderera"],
    21: ["kiosco", "almacen", "despensa", "mini"],
    24: ["cuidado", "niñera", "geriatrico", "adultos mayores"],
    25: ["inmobiliaria", "propiedades", "alquiler"],
    27: ["comuna", "municipalidad", "registro civil", "policia", "comisaria", "bomberos", "emergencias", "gobierno", "municipio", "concejo", "violencia de genero", "144", "911", "epe", "cooperativa", "guardia urbana"],
    28: ["jardin", "escuela", "colegio", "maternal", "apoyo escolar", "clases", "taller de", "matematica", "particular"],
    29: ["escribana", "escribania", "notario"],
    30: ["flete", "mudanza", "cadete", "cadeteria", "comisionista"],
    31: ["imprenta", "impresiones", "grafica"],
    36: ["sanatorio", "hospital", "samco", "clinica", "medico", "odontologo", "odontologia", "kinesiologo", "kinesiologia", "consultorio", "dentista", "dispensario", "ambulancia", "podologa", "salud", "laboratorio"],
    37: ["taller", "reparacion", "service", "aire acondicionado", "cerrajero", "cerrajeria"],
    38: ["mecanico", "repuestos", "auto", "smata"],
    39: ["remis", "taxi", "chofer", "uber", "transporte"],
    40: ["modista", "costura", "costurera", "arreglos"],
    41: ["vivero", "plantas", "jardin"],
    42: ["arquitectura", "arquitecto", "estudio", "gestora", "gestoria"],
    43: ["gym", "gimnasio", "fitness", "entrenamiento"],
    45: ["bicicletero", "bicicleteria", "bicicleta", "bici"]
}

def auto_moderate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    cursor.execute("SELECT id, name, description FROM contacts WHERE category_id = 26")
    others = cursor.fetchall()
    
    updated = 0
    total = len(others)
    
    print(f"Iniciando moderación mejorada (v3) de {total} contactos en 'Otro'...")
    
    for contact_id, name, desc in others:
        text = f"{name} {desc or ''}".lower()
        
        found_cat = None
        for cat_id, keywords in MAPPING.items():
            for kw in keywords:
                # Usar regex con word boundaries para evitar falsos positivos
                pattern = rf"\b{re.escape(kw.lower())}\b"
                if re.search(pattern, text):
                    found_cat = cat_id
                    break
            if found_cat: break
        
        if found_cat:
            cursor.execute("UPDATE contacts SET category_id = ?, updated_at = datetime('now') WHERE id = ?", (found_cat, contact_id))
            updated += 1

    conn.commit()
    conn.close()
    print(f"Moderación completada: {updated} de {total} contactos re-categorizados.")

if __name__ == "__main__":
    auto_moderate()
