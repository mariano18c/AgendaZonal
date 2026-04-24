import sqlite3
import re
import os
import shutil
from pathlib import Path

import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Configuración
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "backend" / "database" / "agenda.db"
SOURCE_DIR = BASE_DIR / "fuente_datos"

# Datos institucionales extraídos de 'Nuevo Documento de texto.txt'
INSTITUTIONAL_DATA = [
    {"name": "Comuna de Ybarlucea", "phone": "+543414904028", "cat": 27, "desc": "Sede administrativa central. Gral. San Martín 1001. Horario: 7:00 a 12:30. Email: comunadeybarlucea@hotmail.com"},
    {"name": "SAMCO Ibarlucea", "phone": "+543414904082", "cat": 36, "desc": "Centro de salud local. Corrientes 141. Ambulancia: +543415692682"},
    {"name": "Agencia de Control Policial", "phone": "08004443583", "cat": 27, "desc": "Línea gratuita 24 hs."},
    {"name": "Cementerio Jardín Ibarlucea", "phone": "+5493413089336", "cat": 27, "desc": "Ruta Provincial 34. Lun-Vie 7:00-12:30; Sáb-Dom 8:00-17:30."},
    {"name": "Estancia Ibarlucea", "phone": "+543415986897", "cat": 17, "desc": "Predio deportivo en Calle 1359 s/n. Abierto 24hs."},
    {"name": "Cooperativa de Energía Ibarlucea", "phone": "+543414904236", "cat": 27, "desc": "Belgrano y Santa Fe. WhatsApp Guardia: +5493416749221. Horario: 7:30 a 12:30."},
    {"name": "Banco Santa Fe (ATM)", "phone": None, "cat": 27, "desc": "Ubicado en San Martín 1001 (edificio de la Comuna)."},
    {"name": "Farmacia García", "phone": None, "cat": 13, "desc": "Consultas al público y servicios farmacéuticos generales en Ibarlucea."},
    {"name": "Farmacia Fedyszyn", "phone": None, "cat": 13, "desc": "Reconocida farmacia por su atención en la zona de Ibarlucea."},
    {"name": "Battilana Gabriel Emilio (Kinesiología)", "phone": "+5493415114199", "cat": 36, "desc": "Servicio de kinesiología en Ibarlucea."},
    {"name": "Franco Fabricio (Kinesiología)", "phone": "+5493414761512", "cat": 36, "desc": "Servicio de kinesiología. Tel alternativo: 0336 154517636."},
]

def normalize_phone(phone):
    if not phone: return None
    digits = re.sub(r"\D", "", phone)
    if not digits: return None
    if digits.startswith("54"): return "+" + digits
    if digits.startswith("0"): digits = digits[1:]
    if len(digits) == 10: return "+549" + digits
    return "+" + digits

def enrich_and_move():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # 1. Enriquecer datos institucionales
    for data in INSTITUTIONAL_DATA:
        phone = normalize_phone(data["phone"])
        cursor.execute("SELECT id FROM contacts WHERE name LIKE ?", (f"%{data['name']}%",))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("""
                UPDATE contacts 
                SET phone = COALESCE(phone, ?), description = ?, category_id = ?, updated_at = datetime('now') 
                WHERE id = ?
            """, (phone, data["desc"], data["cat"], existing[0]))
        else:
            cursor.execute("""
                INSERT INTO contacts (name, phone, category_id, description, status, is_verified, verification_level, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'active', 1, 3, datetime('now'), datetime('now'))
            """, (data["name"], phone, data["cat"], data["desc"]))

    # 2. Mover archivos procesados
    ok_dir = SOURCE_DIR / "importados_ok"
    no_ok_dir = SOURCE_DIR / "importados_no_ok"
    
    ok_dir.mkdir(exist_ok=True)
    no_ok_dir.mkdir(exist_ok=True)
    
    # Listado de archivos para mover (los que ya procesamos)
    files_to_move = [
        "Chat de WhatsApp con Ibarlucea informa📢.txt",
        "contactos.ods",
        "Sin título 1.ods",
        "Nuevo Documento de texto.txt",
        "profesionales_ybarlucea.json",
        "vcf_nuevos.json",
        "contactos_ods.json",
        "profesionales_marketplace.json",
        "real_businesses_ybarlucea.json",
        "vcf",
        "imagenes"
    ]
    
    for item_name in files_to_move:
        src = SOURCE_DIR / item_name
        if src.exists():
            try:
                dest = ok_dir / item_name
                if dest.exists():
                    if dest.is_dir(): shutil.rmtree(dest)
                    else: dest.unlink()
                shutil.move(str(src), str(ok_dir))
                print(f"Moved to OK: {item_name}")
            except Exception as e:
                print(f"Error moving {item_name}: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    enrich_and_move()
