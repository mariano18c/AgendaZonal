import sqlite3
import re
from pathlib import Path

# Configuración
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "agenda.db"

# Datos extraídos manualmente por OCR (Batch 5)
EXTRACTED_DATA_B5 = [
    {"name": "Escuela Primaria (Teléfono provisorio)", "phones": ["3417064685"], "cat": 28, "desc": "Teléfono provisorio para llamadas y Whatsapp mientras se resuelve la situación del teléfono fijo."},
    {"name": "SAMCo Ybarlucea (Campaña PAP)", "phones": [], "cat": 24, "desc": "Campaña de prevención de cáncer cervicouterino. Lunes 30 de Marzo, 9 a 12hs. Sin turno previo."},
    {"name": "Laboratorio (Aviso Paros)", "phones": [], "cat": 24, "desc": "Días sin atención por paro de UNR: 16/03, 31/03, 08/04, 17/04, 23/04."},
    {"name": "CADETERÍA LyR", "phones": ["3417478336"], "cat": 30, "desc": "Servicio de cadetería y mensajería. Envíos en todo Rosario y alrededores. Trámites, compras, documentación."},
    {"name": "EPE (Corte Programado)", "phones": [], "cat": 27, "desc": "Mantenimiento en red de media tensión. Ibarlucea, Pueblo y La Rinconada."},
    {"name": "Feria de Emprendedores (Ybarlucea)", "phones": [], "cat": 27, "desc": "Feria en Plaza San Martín, Mes de la Mujer. Domingo 16:00hs."},
    {"name": "Analía Oviedo (Cuidado de adultos)", "phones": ["3416068377"], "cat": 24, "desc": "Atención de adultos mayores. Hospitales, sanatorios y domicilios particulares. Baño en cama, insulina."},
    {"name": "Biblioteca Julio Migno (Lectura)", "phones": [], "cat": 14, "desc": "Actividad 'Lectura a la Canasta'. Sábado 25/04, 15hs. Traer mate y texto para compartir."},
    {"name": "PETRACCO Servicios Inmobiliarios", "phones": ["3413565711"], "cat": 25, "desc": "Servicios inmobiliarios. Alquiler de locales comerciales en Ibarlucea (Belgrano 881)."},
    {"name": "Alquiler Monoambiente (Particular)", "phones": ["3416640259"], "cat": 25, "desc": "Se alquila monoambiente. Mes para entrar y depósito."},
    {"name": "Salud Animal Ybarlucea (Punto Digital)", "phones": [], "cat": 3, "desc": "Desparasitación, esterilización y vacuna antirrábica. Jueves de Abril 14 a 17hs en Punto Digital."},
    {"name": "Asistencia a Víctimas Siniestros", "phones": ["149"], "cat": 27, "desc": "Red Federal de Asistencia a Víctimas de Siniestros Viales. Opción 2."},
]

def normalize_phone(phone):
    if not phone: return None
    digits = re.sub(r"\D", "", phone)
    if not digits: return None
    if len(digits) == 3: return digits # Emergencias como 149, 911
    if digits.startswith("54"): return "+" + digits
    if digits.startswith("0"): digits = digits[1:]
    if len(digits) == 10: return "+549" + digits
    return "+" + digits

def persist_ocr_b5():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    inserted = 0
    updated = 0
    
    for item in EXTRACTED_DATA_B5:
        name = item["name"]
        raw_phones = item["phones"]
        phone = normalize_phone(raw_phones[0]) if raw_phones else None
        cat_id = item["cat"]
        desc = item["desc"]
        
        if phone:
            cursor.execute("SELECT id FROM contacts WHERE phone = ?", (phone,))
        else:
            cursor.execute("SELECT id FROM contacts WHERE name = ?", (name,))
        
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("UPDATE contacts SET description = ?, category_id = ?, updated_at = datetime('now') WHERE id = ?", (desc, cat_id, existing[0]))
            updated += 1
        else:
            try:
                cursor.execute("""
                    INSERT INTO contacts (name, phone, category_id, description, status, is_verified, verification_level, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'active', 1, 2, datetime('now'), datetime('now'))
                """, (name, phone, cat_id, desc))
                inserted += 1
            except Exception as e:
                print(f"Error insertando {name}: {e}")

    conn.commit()
    conn.close()
    print(f"OCR Batch 5 Persistencia: {inserted} insertados, {updated} actualizados.")

if __name__ == "__main__":
    persist_ocr_b5()
