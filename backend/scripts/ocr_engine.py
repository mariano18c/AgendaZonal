#!/usr/bin/env python3
"""
AgendaZonal - OCR Engine
=========================
Motor de extracción de datos de contacto desde imágenes.

Estrategia dual:
  1. Tesseract OCR (si está instalado) → extracción completa de texto.
  2. Fallback: solo metadata del archivo (nombre, contexto WhatsApp).

Instalar Tesseract:
  - RPi/Linux: sudo apt install tesseract-ocr tesseract-ocr-spa
  - Windows:   https://github.com/UB-Mannheim/tesseract/wiki
               + agregar al PATH
"""
import re
import sqlite3
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Intentar importar pytesseract (opcional)
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
    
    # Configurar path en Windows si existe en la ubicación por defecto
    _win_tess = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if _win_tess.exists():
        pytesseract.pytesseract.tesseract_cmd = str(_win_tess)
        
except ImportError:
    TESSERACT_AVAILABLE = False

# Si solo falta pytesseract pero Pillow está disponible
if not TESSERACT_AVAILABLE:
    try:
        from PIL import Image
        PIL_AVAILABLE = True
    except ImportError:
        PIL_AVAILABLE = False
else:
    PIL_AVAILABLE = True

log = logging.getLogger("ocr_engine")

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "backend" / "database" / "agenda.db"
OCR_OUTPUT_DIR = PROJECT_ROOT / "backend" / "scripts" / "ocr_output"

# ── Mapeo de categorías (reutilizado de auto_moderate_v3) ──────────────────────
CATEGORY_MAP = {
    1: ["plomero", "plomeria", "cloaca"],
    2: ["gasista", "gas matriculado"],
    3: ["electricista", "electricidad", "electrica", "instalacion electrica"],
    4: ["peluqueria", "barberia", "estetica", "manicura", "nails", "peinados"],
    5: ["albañil", "construccion", "reformas", "ceramicos", "membrana"],
    6: ["pintor", "pintura"],
    7: ["carpintero", "carpinteria", "mueble"],
    8: ["supermercado"],
    9: ["carniceria", "carnes", "granja", "frigorifico"],
    10: ["verduleria", "fruteria", "huerta"],
    11: ["panaderia", "reposteria", "tortas", "facturas", "pasteleria", "confiteria"],
    12: ["ropa", "tienda", "indumentaria", "shopping"],
    13: ["farmacia", "medicamento"],
    14: ["libreria", "papeleria"],
    15: ["bar", "cerveceria", "pub"],
    16: ["restaurant", "comida", "vianda", "pizza", "empanada", "rotiseria",
         "hamburgueseria", "delivery"],
    17: ["club", "deportivo"],
    18: ["bazar", "regaleria"],
    19: ["veterinaria", "mascotas", "canino", "felino"],
    20: ["ferreteria", "materiales", "maderera"],
    21: ["kiosco", "almacen", "despensa"],
    24: ["cuidado", "enfermera", "niñera", "geriatrico"],
    25: ["inmobiliaria", "propiedades", "alquiler", "alquilo", "se alquila"],
    27: ["comuna", "municipalidad", "registro civil", "policia", "comisaria",
         "bomberos", "emergencia", "gobierno", "municipio", "cooperativa",
         "guardia urbana", "epe", "corte programado"],
    28: ["jardin", "escuela", "colegio", "maternal", "apoyo escolar", "clases"],
    29: ["escribana", "escribania", "notario"],
    30: ["flete", "mudanza", "cadete", "cadeteria", "envios", "mensajeria"],
    31: ["imprenta", "impresiones", "grafica", "sublimacion"],
    34: ["vinoteca"],
    35: ["heladeria", "helados"],
    36: ["sanatorio", "hospital", "samco", "clinica", "medico", "odontologo",
         "kinesiologo", "consultorio", "dentista", "dispensario",
         "podologa", "salud", "laboratorio", "vacuna"],
    37: ["taller", "reparacion", "service", "aire acondicionado"],
    38: ["mecanico", "mecanica", "repuestos"],
    39: ["remis", "taxi", "chofer", "uber", "transporte"],
    40: ["modista", "costura", "costurera"],
    41: ["vivero", "plantas"],
    42: ["arquitectura", "arquitecto", "diseño", "planos"],
    43: ["gym", "gimnasio", "fitness", "entrenamiento"],
    44: ["cerrajero", "cerrajeria"],
    45: ["bicicletero", "bicicleteria", "bicicleta"],
}


# ── Regex para teléfonos argentinos ────────────────────────────────────────────
PHONE_PATTERNS = [
    # +54 9 341 XXX-XXXX / +549341XXXXXXX
    r"\+?54\s*9?\s*341[\s\-]?\d{3}[\s\-]?\d{4}",
    # 341-XXXXXXX / 341 XXX XXXX
    r"(?<!\d)341[\s\-]?\d{3,4}[\s\-]?\d{4}(?!\d)",
    # 0341-XXXXXXX
    r"0341[\s\-]?\d{3,4}[\s\-]?\d{4}",
    # 15-XXXXXXX (celular local)
    r"(?<!\d)15[\s\-]?\d{3,4}[\s\-]?\d{4}(?!\d)",
    # Números de emergencia cortos
    r"(?<!\d)(911|107|100|101|149|144|147)(?!\d)",
    # WhatsApp genérico (muchos formatos)
    r"(?:whatsapp|wsp|ws|wa)[\s:]*\+?\d[\d\s\-]{8,14}",
]


def normalize_phone(phone: str) -> str | None:
    """Normaliza un teléfono al formato +549XXXXXXXXXX."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None
    # Números de emergencia (3 dígitos)
    if len(digits) <= 3:
        return digits
    # Ya tiene prefijo completo +54 9 341...
    if digits.startswith("549") and len(digits) == 13:
        return "+" + digits
    if digits.startswith("54") and len(digits) == 12:
        # +54 341... → insertar 9
        return "+549" + digits[2:]
    if digits.startswith("54"):
        return "+" + digits
    # 0341...
    if digits.startswith("0"):
        digits = digits[1:]
    # 15XXXXXXX (celular local, asume 341)
    if digits.startswith("15") and len(digits) == 10:
        return "+549341" + digits[2:]
    # 341XXXXXXX (10 dígitos)
    if len(digits) == 10:
        return "+549" + digits
    # 7 dígitos (local Rosario, asume 341)
    if len(digits) == 7:
        return "+549341" + digits
    return "+" + digits if len(digits) > 5 else None


def extract_phones(text: str) -> list[str]:
    """Extrae y normaliza todos los teléfonos encontrados en un texto."""
    phones = []
    seen = set()
    for pattern in PHONE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw = match.group(0)
            # Limpiar prefijo "whatsapp:" si lo tiene
            raw = re.sub(r"(?i)(?:whatsapp|wsp|ws|wa)[\s:]*", "", raw)
            normalized = normalize_phone(raw)
            if normalized and normalized not in seen:
                phones.append(normalized)
                seen.add(normalized)
    return phones


def guess_category(text: str) -> int:
    """Adivina la categoría de un contacto basándose en palabras clave."""
    text_lower = text.lower()
    for cat_id, keywords in CATEGORY_MAP.items():
        for kw in keywords:
            # Usar regex con word boundaries para evitar falsos positivos
            # ej: 'bar' no debe matchear con 'Ibarlucea'
            pattern = rf"\b{re.escape(kw.lower())}\b"
            if re.search(pattern, text_lower):
                return cat_id
    return 26  # Otro


def extract_name_from_text(text: str) -> str | None:
    """Intenta extraer un nombre de negocio/persona del texto OCR."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return None

    # La primera línea con contenido significativo suele ser el título/nombre
    for line in lines[:5]:
        # Ignorar líneas que son solo números o muy cortas
        if len(line) < 3:
            continue
        if re.match(r"^[\d\s\-\+\(\)]+$", line):
            continue
        # Ignorar líneas que parecen direcciones
        if re.search(r"(?i)(calle|av\.|avenida|ruta|esquina|entre)", line):
            continue
        # Ignorar líneas de horario
        if re.search(r"\d{1,2}:\d{2}", line):
            continue
        # Candidato a nombre (limpiar)
        name = re.sub(r"[^\w\s\-\.áéíóúñÁÉÍÓÚÑ]", "", line).strip()
        if len(name) >= 3:
            return name[:80]  # Limitar largo

    return None


def ocr_image(filepath: Path) -> str:
    """
    Ejecuta OCR sobre una imagen y devuelve el texto extraído.
    """
    if not TESSERACT_AVAILABLE:
        return ""

    if getattr(ocr_image, "_tesseract_missing", False):
        return ""

    try:
        img = Image.open(filepath)
        if img.mode != "L":
            img = img.convert("L")

        # Configuración de tessdata local si existe
        local_tessdata = PROJECT_ROOT / "backend" / "scripts" / "tessdata"
        config = "--psm 6"
        if local_tessdata.exists():
            config += f' --tessdata-dir "{local_tessdata}"'

        # Intentar con idioma español
        try:
            text = pytesseract.image_to_string(img, lang="spa", config=config)
        except Exception:
            # Fallback a idioma por defecto si falla spa
            text = pytesseract.image_to_string(img, config="--psm 6")

        return text.strip()

    except Exception as e:
        err_msg = str(e).lower()
        if "not installed" in err_msg or "not in your path" in err_msg:
            # Marcar como no disponible para no reintentar
            ocr_image._tesseract_missing = True
            log.warning(
                "Tesseract no instalado. "
                "RPi: sudo apt install tesseract-ocr tesseract-ocr-spa | "
                "Windows: https://github.com/UB-Mannheim/tesseract/wiki"
            )
        else:
            log.error(f"Error OCR en {filepath.name}: {e}")
        return ""


def process_single_image(filepath: Path) -> dict | None:
    """
    Procesa una imagen y devuelve un dict con los datos extraídos,
    o None si no se pudo extraer información útil.
    """
    result = {
        "source_file": filepath.name,
        "name": None,
        "phones": [],
        "category_id": 26,
        "description": "",
        "ocr_text": "",
        "confidence": "low",
    }

    # 1. Intentar OCR
    ocr_text = ocr_image(filepath)
    result["ocr_text"] = ocr_text

    if ocr_text:
        # 2. Extraer teléfonos
        result["phones"] = extract_phones(ocr_text)

        # 3. Adivinar categoría
        result["category_id"] = guess_category(ocr_text)

        # 4. Extraer nombre
        name = extract_name_from_text(ocr_text)
        if name:
            result["name"] = name

        # 5. Generar descripción (primeras 200 chars del OCR limpio)
        desc_lines = [l.strip() for l in ocr_text.split("\n") if l.strip()]
        result["description"] = " | ".join(desc_lines[:3])[:200]

        # 6. Calcular confianza
        has_phone = len(result["phones"]) > 0
        has_name = result["name"] is not None
        has_category = result["category_id"] != 26
        if has_phone and has_name and has_category:
            result["confidence"] = "high"
        elif has_phone or (has_name and has_category):
            result["confidence"] = "medium"

    # Fallback: usar nombre del archivo como pista
    if not result["name"]:
        # IMG-20260329-WA0001.jpg → no sirve
        stem = filepath.stem
        if not re.match(r"^IMG[-_]\d+", stem, re.IGNORECASE):
            result["name"] = stem.replace("-", " ").replace("_", " ").title()

    return result if (result["phones"] or result["name"]) else None


def persist_ocr_result(result: dict) -> bool:
    """Persiste un resultado OCR en la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")

    phone = result["phones"][0] if result["phones"] else None
    name = result["name"] or f"OCR Import - {result['source_file']}"

    # Verificar duplicado por teléfono
    if phone:
        cursor.execute("SELECT id FROM contacts WHERE phone = ?", (phone,))
        existing = cursor.fetchone()
        if existing:
            # Actualizar descripción si estaba vacía y asignar photo_path
            cursor.execute(
                "UPDATE contacts SET description = COALESCE(NULLIF(description, ''), ?), photo_path = COALESCE(photo_path, ?), updated_at = datetime('now') WHERE id = ?",
                (result["description"], result["source_file"], existing[0])
            )
            conn.commit()
            conn.close()
            return True  # Ya existía, actualizado

    # Insertar nuevo contacto
    # Los OCR van como 'pending' para revisión humana
    status = "active" if result["confidence"] == "high" else "pending"
    verification_level = 2 if result["confidence"] == "high" else 1

    try:
        cursor.execute("""
            INSERT INTO contacts (name, phone, category_id, description, status,
                                  is_verified, verification_level, photo_path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?, datetime('now'), datetime('now'))
        """, (name, phone, result["category_id"], result["description"],
              status, verification_level, result["source_file"]))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error(f"Error persistiendo OCR result: {e}")
        conn.close()
        return False


def process_image_batch(image_paths: list[Path]) -> dict:
    """
    Procesa un lote de imágenes y devuelve estadísticas.
    Llamado desde el watcher o manualmente.
    """
    stats = {"processed": 0, "persisted": 0, "skipped": 0, "errors": 0}
    results = []

    for filepath in image_paths:
        if not filepath.exists():
            continue
        stats["processed"] += 1

        try:
            result = process_single_image(filepath)
            if result:
                results.append(result)
                ok = persist_ocr_result(result)
                if ok:
                    stats["persisted"] += 1
                else:
                    stats["errors"] += 1
            else:
                stats["skipped"] += 1
                log.info(f"Sin datos extraibles: {filepath.name}")
        except Exception as e:
            stats["errors"] += 1
            log.error(f"Error procesando {filepath.name}: {e}")

    # Guardar resultados JSON para auditoría
    if results:
        OCR_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OCR_OUTPUT_DIR / f"ocr_batch_{timestamp}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        log.info(f"Resultados OCR guardados en: {output_file.name}")

    return stats


# ── CLI: Uso directo ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 60)
    print("AgendaZonal OCR Engine")
    print(f"Tesseract disponible: {'SI' if TESSERACT_AVAILABLE else 'NO'}")
    print(f"Pillow disponible:    {'SI' if PIL_AVAILABLE else 'NO'}")
    print("=" * 60)

    # Procesar argumentos: puede recibir paths o carpeta
    if len(sys.argv) > 1:
        paths = []
        for arg in sys.argv[1:]:
            p = Path(arg)
            if p.is_dir():
                paths.extend(p.glob("*.jpg"))
                paths.extend(p.glob("*.jpeg"))
                paths.extend(p.glob("*.png"))
            elif p.is_file():
                paths.append(p)
        if paths:
            stats = process_image_batch(paths)
            print(f"\nResultados: {json.dumps(stats, indent=2)}")
        else:
            print("No se encontraron imágenes para procesar.")
    else:
        # Default: procesar ./fuente_datos/imagenes/
        img_dir = PROJECT_ROOT / "fuente_datos" / "imagenes"
        if img_dir.exists():
            paths = list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.jpeg")) + list(img_dir.glob("*.png"))
            if paths:
                print(f"Procesando {len(paths)} imagenes de {img_dir}...")
                stats = process_image_batch(paths)
                print(f"\nResultados: {json.dumps(stats, indent=2)}")
            else:
                print(f"No hay imagenes en {img_dir}")
        else:
            print(f"Carpeta no encontrada: {img_dir}")
            print("Uso: python ocr_engine.py [carpeta_imagenes | imagen1.jpg imagen2.jpg ...]")
