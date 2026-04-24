import os
import re
import json
from pathlib import Path

# Configuración
BASE_DIR = Path(__file__).resolve().parent.parent
VCF_DIR = BASE_DIR.parent / "fuente_datos" / "vcf"
OUTPUT_FILE = BASE_DIR / "scripts" / "vcard_candidates.json"

# Mapeo simple de palabras clave a IDs de categoría (basado en init_db.py)
CATEGORY_MAP = {
    r"plomero|plomeria": 100,
    r"gasista|gas": 101,
    r"electri": 102,
    r"peluquer|barber": 103,
    r"albañil": 104,
    r"pintor": 105,
    r"carpinte": 106,
    r"supermercado": 107,
    r"carnicer": 108,
    r"verduler": 109,
    r"panader": 110,
    r"tienda|ropa": 111,
    r"farmacia": 112,
    r"libreria": 113,
    r"bar": 114,
    r"restauran": 115,
    r"club": 116,
    r"bazar": 117,
    r"veterinari|vete": 118,
    r"ferreteria": 119,
    r"kiosco|almacen": 120,
    r"jugueteria": 121,
    r"polirrubro": 122,
    r"cuidado|salud": 123,
    r"alquiler": 124,
    r"comuna|municipio|samco|dispensario|policia|comisaria": 125,
    r"apoyo|escuela": 126,
    r"escriban": 127,
    r"flete|remis|uber|transporte": 128,
    r"imprenta|impresion": 129,
    r"vinoteca": 130,
    r"helader": 131,
    r"sanatorio": 132,
    r"taller": 133,
    r"mecanico": 134,
}

def normalize_phone(phone):
    """Limpia y normaliza el teléfono al formato +549..."""
    if not phone:
        return None
    
    # Solo nos quedamos con dígitos y el signo + inicial si existe
    digits = re.sub(r"(?<!^)\+|[^\d+]", "", phone)
    if not digits: return None
    
    # Si tiene el +, lo quitamos para normalizar
    has_plus = digits.startswith("+")
    num = digits[1:] if has_plus else digits
    
    # Casos comunes en Argentina
    if num.startswith("54"):
        if len(num) == 12 and num[2] != "9": # 54 341 ... -> 54 9 341 ...
            num = "549" + num[2:]
        return "+" + num
    
    if num.startswith("0"):
        num = num[1:]
        
    if len(num) == 10: # 341 ...
        return "+549" + num
    
    return "+" + num if num else None

def guess_category(name):
    """Intenta adivinar la categoría basada en el nombre."""
    name_lower = name.lower()
    for pattern, cat_id in CATEGORY_MAP.items():
        if re.search(pattern, name_lower):
            return cat_id
    return 999 # Otro

def parse_vcf(file_path):
    """Parsea un archivo VCF básico."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        name = ""
        # Intentar extraer FN (Full Name)
        fn_match = re.search(r"FN:(.*)", content)
        if fn_match:
            name = fn_match.group(1).strip()
            
        # Si no hay FN, usar N
        if not name:
            n_match = re.search(r"N:(.*?);(.*?);", content)
            if n_match:
                last, first = n_match.groups()
                name = f"{first} {last}".strip()
        
        # Si sigue sin nombre, usar el nombre del archivo
        if not name:
            name = file_path.stem
        
        phones = []
        # Intentar extraer teléfono del nombre por si el FN es un número
        possible_phone = normalize_phone(name)
        if possible_phone:
            phones.append(possible_phone)

        # Extraer teléfono (TEL)
        # Soporta TEL;TYPE=CELL, TEL;waid=..., etc.
        # Buscamos el contenido después del ÚLTIMO dos puntos de la línea TEL
        tel_matches = re.findall(r"TEL.*:(.*)", content)
        for tel in tel_matches:
            clean_tel = normalize_phone(tel.strip())
            if clean_tel and clean_tel not in phones:
                phones.append(clean_tel)
                
        # Extraer Email
        email = None
        email_match = re.search(r"EMAIL.*?:(.*)", content)
        if email_match:
            email = email_match.group(1).strip()

        return {
            "name": name,
            "phones": phones,
            "email": email,
            "category_id": guess_category(name),
            "source": file_path.name
        }
    except Exception as e:
        print(f"Error parseando {file_path}: {e}")
        return None

def main():
    if not VCF_DIR.exists():
        print(f"Error: Directorio {VCF_DIR} no encontrado.")
        return

    candidates = []
    vcf_files = list(VCF_DIR.glob("*.vcf"))
    print(f"Procesando {len(vcf_files)} archivos VCF...")

    for vcf_path in vcf_files:
        data = parse_vcf(vcf_path)
        if data and data["phones"]:
            candidates.append(data)

    # Guardar resultados
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=4, ensure_ascii=False)

    print(f"Éxito: {len(candidates)} candidatos guardados en {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
