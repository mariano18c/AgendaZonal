import sqlite3
import re
from pathlib import Path

# Configuración
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "agenda.db"

# Datos extraídos manualmente por OCR (Batch 1-4)
EXTRACTED_DATA = [
    {"name": "AFFUR REPP", "phones": ["3413643048", "3413638792"], "cat": 37, "desc": "Instalación de aires acondicionados, Electricidad, Reparación de lavarropas. IG: AFFUR.REPARACIONES"},
    {"name": "Joel (Oficial Plomero Gasista)", "phones": ["3416967628"], "cat": 1, "desc": "Plomero y Gasista. Puntualidad y responsabilidad."},
    {"name": "CELUFIX", "phones": ["3416214574", "3413027886"], "cat": 37, "desc": "Reparación de computadoras y celulares, desbloqueos, cambios de módulos y baterías. IG: @celufix___"},
    {"name": "Juzgado Comunitario de Pequeñas Causas", "phones": ["3414710775"], "cat": 27, "desc": "Pueyrredón 917, Granadero Baigorria. Orientación legal gratuita en temas laborales y civiles."},
    {"name": "Franco Baez (Gasista matriculado)", "phones": ["3412588962"], "cat": 2, "desc": "Instalaciones y reparaciones de gas, agua y desagües. Trámites en litoral gas."},
    {"name": "EL REY DE LA LEÑA", "phones": ["3416768955"], "cat": 23, "desc": "Venta de leña por pedido."},
    {"name": "BAHIA AVENTURA", "phones": ["3413870716"], "cat": 17, "desc": "Alquiler de inflables, juegos (ping pong, metegol), livings y cátering para eventos."},
    {"name": "MANTENIMIENTO E INSTALACIONES (3413768013)", "phones": ["3413768013"], "cat": 37, "desc": "Electricidad, Plomería, Herrería. Bombas, piscinas, calderas."},
    {"name": "Pablo Peralta (Bicicletería)", "phones": ["3416851264"], "cat": 37, "desc": "Arreglo de bicicletas a domicilio. Suipacha 352a, Barrio Espinillo, Ibarlucea."},
    {"name": "Fletes y mudanzas 09", "phones": ["3412031806"], "cat": 30, "desc": "Flete, mudanzas, cadetería, comisionista. Los 365 días del año."},
    {"name": "AYL PERFORACIONES", "phones": ["3416488340", "3412140502"], "cat": 37, "desc": "Perforaciones para agua subterránea, reparación de bombas, bobinado de motores."},
    {"name": "Biblioteca (la Biblio)", "phones": [], "cat": 14, "desc": "Horarios: Lun/Mar/Vie 12-18hs, Jue 12-17hs."},
    {"name": "Bomberos Voluntarios G. Baigorria", "phones": [], "cat": 27, "desc": "ALIAS: PIBA.CURVA.DULCE. CBU: 0110140520014000310591. Asociación para colaboración."},
    {"name": "Pediatría SAMCo Ybarlucea", "phones": [], "cat": 24, "desc": "Dra Mora (Lun/Mie/Vie am), Dra Estebenet (Mar am, Mie pm), Dr Farrugia (Jue 14hs)."},
    {"name": "COM Roldán (Fauna)", "phones": ["5299300"], "cat": 27, "desc": "Centro de Operaciones Municipal. Consulta por fauna autóctona."},
    {"name": "Curso de Barbería (Andrea)", "phones": ["3416157533"], "cat": 4, "desc": "Maipú 225 - Ibarlucea. Formación práctica."},
    {"name": "Agua de Mesa Holy Water", "phones": ["3413670341"], "cat": 16, "desc": "Venta de agua de mesa. Búsqueda de personal."},
    {"name": "CoopIbarlucea (Administración)", "phones": ["3416749221"], "cat": 27, "desc": "Cooperativa de Energía y Consumos de Ibarlucea."},
    {"name": "CoopIbarlucea (Guardia Energía)", "phones": ["3413771700"], "cat": 27, "desc": "Guardia de reclamos eléctricos."},
    {"name": "CoopIbarlucea (Internet)", "phones": ["3412616365"], "cat": 27, "desc": "Servicio técnico internet."},
    {"name": "SAMCo Ibarlucea (Nuevo número)", "phones": ["3413035280"], "cat": 24, "desc": "Nuevo número de contacto disponible (solo llamadas)."},
]

def normalize_phone(phone):
    if not phone: return None
    digits = re.sub(r"\D", "", phone)
    if not digits: return None
    if digits.startswith("54"): return "+" + digits
    if digits.startswith("0"): digits = digits[1:]
    if len(digits) == 10: return "+549" + digits
    return "+" + digits

def persist_ocr():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    inserted = 0
    updated = 0
    
    for item in EXTRACTED_DATA:
        name = item["name"]
        raw_phones = item["phones"]
        phone = normalize_phone(raw_phones[0]) if raw_phones else None
        cat_id = item["cat"]
        desc = item["desc"]
        
        # Verificar si ya existe por nombre o teléfono
        if phone:
            cursor.execute("SELECT id FROM contacts WHERE phone = ?", (phone,))
        else:
            cursor.execute("SELECT id FROM contacts WHERE name = ?", (name,))
        
        existing = cursor.fetchone()
        
        if existing:
            # Actualizar descripción si es necesario
            cursor.execute("UPDATE contacts SET description = ?, category_id = ?, updated_at = datetime('now') WHERE id = ?", (desc, cat_id, existing[0]))
            updated += 1
        else:
            # Insertar nuevo
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
    print(f"OCR Persistencia: {inserted} insertados, {updated} actualizados.")

if __name__ == "__main__":
    persist_ocr()
