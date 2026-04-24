import pandas as pd
import sqlite3
import re
from pathlib import Path

# Configuración
BASE_DIR = Path(__file__).resolve().parent.parent
ODS_FILE = BASE_DIR.parent / "fuente_datos" / "Sin título 1.ods"
DB_PATH = BASE_DIR / "database" / "agenda.db"

# Mapeo de categorías (IDs reales de la DB)
CATEGORY_MAP = {
    r"plomer|gas": 1,
    r"electrici": 3,
    r"peluquer|estetica": 4,
    r"albañil": 5,
    r"pintor": 6,
    r"carpinter": 7,
    r"alimentos|comida|vianda": 16, # Restaurant/Comida
    r"farmacia": 13,
    r"veterinari": 19,
    r"ferreteria": 20,
    r"kiosco|almacen": 21,
    r"alquiler": 25,
    r"flete|remis|transporte|mudanza": 30,
    r"taller|reparacion|pc|celular|moto": 37,
    r"mecanico": 38,
    r"odontolog|podolog|enfermer|salud": 24,
    r"ley|legal|escriban": 29,
    r"grafica|imprenta": 31,
    r"climatizac": 37,
    r"evento|entretenimiento": 17,
    r"leña|varios": 23,
    r"herrer": 37, # Taller/Oficio
    r"pileta|jardin|parque": 37,
}

def normalize_phone(phone):
    if pd.isna(phone): return None
    phone = str(phone)
    digits = re.sub(r"\D", "", phone)
    if not digits: return None
    if digits.startswith("54"):
        if len(digits) == 12 and digits[2] != "9": digits = "549" + digits[2:]
        return "+" + digits
    if digits.startswith("0"): digits = digits[1:]
    if len(digits) == 10: return "+549" + digits
    return "+" + digits

def guess_category(rubro):
    if pd.isna(rubro): return 26
    rubro_lower = str(rubro).lower()
    for pattern, cat_id in CATEGORY_MAP.items():
        if re.search(pattern, rubro_lower):
            return cat_id
    return 26

def ingest_ods():
    if not ODS_FILE.exists():
        print(f"Error: No se encontró {ODS_FILE}")
        return

    print(f"Leyendo ODS: {ODS_FILE.name}...")
    df = pd.read_excel(ODS_FILE, engine="odf")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")

    inserted = 0
    skipped = 0
    
    for _, row in df.iterrows():
        rubro = row['Rubro / Servicio']
        nombre = row['Nombre / Marca']
        contacto = row['Contacto Principal']
        detalles = row['Otros Datos / Detalles']
        
        # Saltar filas de encabezado repetidas o vacías
        if pd.isna(nombre) or nombre == 'Nombre / Marca':
            continue
            
        name = str(nombre).strip()
        phone = normalize_phone(contacto)
        category_id = guess_category(rubro)
        description = str(detalles).strip()[:500] if not pd.isna(detalles) else ""
        
        # Evitar duplicados por teléfono
        if phone:
            cursor.execute("SELECT id FROM contacts WHERE phone = ?", (phone,))
            if cursor.fetchone():
                skipped += 1
                continue
        
        try:
            cursor.execute("""
                INSERT INTO contacts (name, phone, category_id, description, status, is_verified, verification_level, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'active', 1, 1, datetime('now'), datetime('now'))
            """, (name, phone, category_id, description))
            inserted += 1
        except Exception as e:
            print(f"Error insertando {name}: {e}")
            skipped += 1

    conn.commit()
    conn.close()
    
    print("\n--- Resumen de Ingesta ODS ---")
    print(f"  Insertados: {inserted}")
    print(f"  Omitidos (duplicados): {skipped}")
    print(f"  Total procesados: {len(df)}")

if __name__ == "__main__":
    ingest_ods()
