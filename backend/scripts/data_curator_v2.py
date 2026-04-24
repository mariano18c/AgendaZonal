import os
import re
import json
from pathlib import Path

# Configuración
BASE_DIR = Path(__file__).resolve().parent.parent
VCF_DIR = BASE_DIR.parent / "fuente_datos" / "vcf"
CHAT_FILE = BASE_DIR.parent / "fuente_datos" / "Chat de WhatsApp con Ibarlucea informa📢.txt"
OUTPUT_FILE = BASE_DIR / "scripts" / "contacts_enriched.json"

# Mapeo corregido basado en IDs reales de la DB (verificado por SELECT)
CATEGORY_MAP = {
    r"plomero|plomeria|destape": 1,
    r"gasista|gas|matriculado": 2,
    r"electri|electricidad|tension|luz": 3,
    r"peluquer|barber|estetica|manicura|pedicura|podolog|uñas|pelo": 4,
    r"albañil|revoque|construccion": 5,
    r"pintor|pintura": 6,
    r"carpinte|mueble": 7,
    r"supermercado|super": 8,
    r"carnicer|frigorifico": 9,
    r"verduler|fruteria": 10,
    r"panader|pasteler|reposter|tortas|facturas|pan": 11,
    r"tienda|ropa|indumentaria|modista|costurera|remera|zapat": 12,
    r"farmacia|begnis|medicamento": 13,
    r"libreria": 14,
    r"bar|cerveza|pub": 15,
    r"restauran|comida|vianda|pizzas|empanadas|roti|sabor|hamburgue": 16,
    r"club": 17,
    r"bazar|regaleria": 18,
    r"veterinari|vete|perro|gato|animal|mascota": 19,
    r"ferreteria": 20,
    r"kiosco|almacen|despensa": 21,
    r"jugueteria": 22,
    r"polirrubro": 23,
    r"cuidado|salud|enfermer|doctor|odontolog|dentista|pediatra|psicolog": 24,
    r"alquiler|quinta|temporario|casa|pabellon|monoambiente": 25,
    r"comuna|municipio|samco|dispensario|policia|comisaria|guardia|juzgado|registro civil": 27,
    r"apoyo|escuela|clases|particular|secundaria|primaria|maestra|jardin": 28,
    r"escriban|notario": 29,
    r"flete|remis|uber|transporte|comisionista|cadete|envios": 30,
    r"imprenta|impresion|sublimacion|grafica": 31,
    r"vinoteca|bebidas": 34,
    r"helader": 35,
    r"sanatorio|hospital": 36,
    r"taller|lavarropa|secarropa|heladera|tecnico|arreglo|bici|moto|auto": 37,
    r"mecanico|motor": 38,
}

def normalize_phone(phone):
    if not phone: return None
    # Solo nos quedamos con dígitos y el signo + inicial si existe
    digits = re.sub(r"(?<!^)\+|[^\d+]", "", phone)
    if not digits: return None
    
    # Si tiene el +, lo quitamos para normalizar
    has_plus = digits.startswith("+")
    num = digits[1:] if has_plus else digits
    
    if num.startswith("54"):
        if len(num) == 12 and num[2] != "9": num = "549" + num[2:]
        return "+" + num
    if num.startswith("0"): num = num[1:]
    if len(num) == 10: return "+549" + num
    return "+" + num if num else None

def guess_category(text):
    if not text: return 26 # Otro
    text_lower = text.lower()
    for pattern, cat_id in CATEGORY_MAP.items():
        if re.search(pattern, text_lower):
            return cat_id
    return 26 # Otro

def parse_chat_context():
    context_map = {}
    if not CHAT_FILE.exists(): return context_map
    try:
        with open(CHAT_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        last_intent_cat = None
        for i, line in enumerate(lines):
            if "?" in line or "alguien" in line.lower() or "algun" in line.lower():
                last_intent_cat = guess_category(line)
            if last_intent_cat and last_intent_cat != 26:
                for j in range(i, min(i+3, len(lines))):
                    vcf_match = re.search(r"‎?(.*?\.vcf)", lines[j])
                    if vcf_match: context_map[vcf_match.group(1).strip()] = last_intent_cat
                    phones = re.findall(r"(\d{2,}\s?\d{3,}\s?\d{4,})", lines[j])
                    for p in phones:
                        norm_p = normalize_phone(p)
                        if norm_p: context_map[norm_p] = last_intent_cat
        return context_map
    except Exception as e:
        print(f"Error analizando chat: {e}")
        return context_map

def parse_vcf(file_path, context_map):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        entries = content.split("BEGIN:VCARD")
        results = []
        for entry in entries:
            if "END:VCARD" not in entry: continue
            name = ""
            fn_match = re.search(r"FN:(.*)", entry)
            if fn_match: name = fn_match.group(1).strip()
            if not name:
                n_match = re.search(r"N:(.*?);(.*?);", entry)
                if n_match:
                    last, first = n_match.groups()
                    name = f"{first} {last}".strip()
            if not name: name = file_path.stem
            phones = []
            
            # Intentar extraer teléfono del nombre por si el FN es un número
            possible_phone = normalize_phone(name)
            if possible_phone:
                phones.append(possible_phone)
                
            # Buscamos el contenido después del ÚLTIMO dos puntos de la línea TEL
            tel_matches = re.findall(r"TEL.*:(.*)", entry)
            for tel in tel_matches:
                clean_tel = normalize_phone(tel.strip())
                if clean_tel and clean_tel not in phones: phones.append(clean_tel)
            if not phones: continue
            cat_id = context_map.get(file_path.name, None)
            if not cat_id:
                for p in phones:
                    if p in context_map:
                        cat_id = context_map[p]
                        break
            if not cat_id or cat_id == 26: cat_id = guess_category(name)
            results.append({"name": name, "phones": phones, "category_id": cat_id, "source": file_path.name})
        return results
    except Exception as e:
        print(f"Error parseando {file_path}: {e}")
        return []

def main():
    context_map = parse_chat_context()
    all_contacts = []
    seen_phones = set()
    for vcf_path in VCF_DIR.glob("*.vcf"):
        entries = parse_vcf(vcf_path, context_map)
        for entry in entries:
            main_phone = entry["phones"][0]
            if main_phone not in seen_phones:
                all_contacts.append(entry)
                seen_phones.add(main_phone)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_contacts, f, indent=4, ensure_ascii=False)
    print(f"Éxito: {len(all_contacts)} contactos enriquecidos guardados con IDs reales.")

if __name__ == "__main__":
    main()
