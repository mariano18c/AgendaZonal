#!/usr/bin/env python3
"""
Script to consolidate all collected data (VCF + JSON) and import to database.
- Parse all VCF files from contactos folder
- Combine with existing JSON data
- Filter by distance (20km from Ybarlucea center)
- Assign default city (Ybarlucea/Ibarlucea) for contacts without zone
- Generate unified JSON for import
- Import to database

Centro de Ybarlucea: -32.8833, -60.7833
"""

import json
import os
import re
import sqlite3
import math
import glob
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
CONTACTOS_DIR = SCRIPT_DIR / "contactos"
DB_PATH = SCRIPT_DIR.parent / "database" / "agenda.db"
OUTPUT_JSON = SCRIPT_DIR / "consolidated_contacts.json"

# Ybarlucea center coordinates
YBARLUCEA_LAT = -32.8833
YBARLUCEA_LON = -60.7833
MAX_DISTANCE_KM = 20.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees).
    Returns distance in kilometers.
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth radius in kilometers
    r = 6371
    
    return c * r


def guess_category_from_name(name: str) -> Optional[int]:
    """
    Guess category ID from contact name using keywords.
    Returns category_id (old code system: 100-122, 999)
    """
    name_lower = name.lower()
    
    # Keywords mapping to category codes
    keywords = {
        # 100 - Plomero
        100: ['plomero', 'plomería', 'agua', 'desagot', 'bomba', 'presurizador', 'cañería', 'cloaca'],
        # 101 - Gasista
        101: ['gasista', 'gasista matriculado', 'caldera', 'calefón', 'estufa a gas', 'service gas'],
        # 102 - Electricista
        102: ['electricista', 'electricidad', 'eléctrico', 'luz', 'cable', 'técnico eléctrico'],
        # 103 - Peluquería/Barbería
        103: ['peluquería', 'peluqueria', 'barbería', 'barberia', 'estilista', 'salón de belleza', 'cosmetología', 'estética'],
        # 104 - Albañil
        104: ['albañil', 'albañilería', 'construcción', 'constructor', 'obra', 'revoque', 'cerámico', 'porcelanato'],
        # 105 - Pintor
        105: ['pintor', 'pintura', 'pinturería', 'decoración'],
        # 106 - Carpintero
        106: ['carpintero', 'carpintería', 'madera', 'muebles', 'ebanista'],
        # 107 - Supermercado
        107: ['supermercado', 'super', 'autoservicio', 'almacén', 'minimercado', 'chino'],
        # 108 - Carnicería
        108: ['carnicería', 'carniceria', 'carnes', 'fiambrería'],
        # 109 - Verdulería
        109: ['verdulería', 'verduleria', 'verduras', 'frutas', 'hortalizas'],
        # 110 - Panadería
        110: ['panadería', 'panaderia', 'panadería', 'pastelería', 'facturas', 'pastas'],
        # 111 - Tienda de ropa
        111: ['tienda', 'ropa', 'indumentaria', 'boutique', 'moda'],
        # 112 - Farmacia
        112: ['farmacia', 'farmacéutico', 'medicamento'],
        # 113 - Librería
        113: ['librería', 'libreria', 'libros', 'papelería', 'útiles'],
        # 114 - Bar
        114: ['bar', 'café', 'cafetería', 'pub', 'bebida'],
        # 115 - Restaurant
        115: ['restaurant', 'restaurante', 'comida', 'rotisería', 'pizza', 'empanadas', 'delivery'],
        # 116 - Club
        116: ['club', 'social', 'centro comunitario'],
        # 117 - Bazar
        117: ['bazar', 'regalos', 'artículos del hogar'],
        # 118 - Veterinaria
        118: ['veterinaria', 'veterinario', 'mascota', 'perro', 'gato', 'clinica animal'],
        # 119 - Ferretería
        119: ['ferretería', 'ferreteria', 'herramientas', 'tornillos', 'chapas', 'perfiles'],
        # 120 - Kiosco
        120: ['kiosco', 'diarios', 'revistas'],
        # 121 - Juguetería
        121: ['juguetería', 'jugueteria', 'juguetes'],
        # 122 - Polirrubro
        122: ['variedades', 'todo', 'polirrubro', 'bazar'],
        # 999 - Otro
        999: ['remis', 'taxi', 'mecánico', 'taller', 'consultorio', 'escuela', 'colegio', 'jardin', 'gimnasio', 'gym', 'consultorios', 'odontologo', 'dentista', 'kinesiologo', 'fisioterapia', 'gestoría', 'gestor', 'imprent', 'gráfica', 'flete', 'mudanza']
    }
    
    for category_id, words in keywords.items():
        for word in words:
            if word in name_lower:
                return category_id
    
    return None


def parse_vcf_file(filepath: Path) -> dict:
    """
    Parse a VCF file and extract contact information.
    Returns a dictionary with contact data.
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        logger.warning(f"Error reading {filepath}: {e}")
        return None
    
    if not content.strip():
        return None
    
    # Extract name from FN (Formatted Name) or filename
    name = None
    phone = None
    
    # Find FN (Formatted Name)
    fn_match = re.search(r'FN[;:](.+?)(?:\r?\n|\r|$)', content)
    if fn_match:
        name = fn_match.group(1).strip()
    
    # If no FN, try to get from N field
    if not name:
        n_match = re.search(r'N[;:]([^;\r\n]+)', content)
        if n_match:
            # N format is: Last;First;Middle;Prefix;Suffix
            parts = n_match.group(1).split(';')
            # Reverse the order (N is Last;First but FN is First Last)
            name_parts = [p.strip() for p in parts if p.strip()]
            name = ' '.join(reversed(name_parts))
    
    # If still no name, use filename
    if not name:
        name = filepath.stem
    
    # Extract phone numbers
    phone_matches = re.findall(r'TEL[;:](?:[^:\r\n]+:)?\s*(?:\+?54\s*)?9?\s*[\d\s\-\(\)]+', content)
    if phone_matches:
        # Clean up phone number
        phone = phone_matches[0]
        # Remove TEL;waid= and other prefixes
        phone = re.sub(r'^(?:TEL|item\d+\.TEL)[;:]', '', phone)
        phone = re.sub(r'waid=\+?54\s*9?\s*', '', phone)
        phone = phone.strip()
        # Normalize: replace multiple spaces with single
        phone = re.sub(r'\s+', ' ', phone)
    
    if not name:
        return None
    
    return {
        'name': name,
        'phone': phone or '',
        'source': 'vcf:' + filepath.name
    }


def parse_all_vcf_files() -> list:
    """
    Parse all VCF files in the contactos directory.
    Returns list of contact dictionaries.
    """
    contacts = []
    vcf_files = list(CONTACTOS_DIR.glob("*.vcf"))
    
    logger.info(f"Found {len(vcf_files)} VCF files")
    
    for vcf_file in vcf_files:
        contact = parse_vcf_file(vcf_file)
        if contact and contact.get('name'):
            # Guess category from name
            category_id = guess_category_from_name(contact['name'])
            if category_id:
                contact['category_id'] = category_id
            
            # Add default coordinates (Ybarlucea center) - will be used for filtering
            contact['latitude'] = YBARLUCEA_LAT
            contact['longitude'] = YBARLUCEA_LON
            contact['distance_km'] = 0.0  # Assume it's in the zone
            
            # Default city
            contact['city'] = 'Ibarlucea'
            contact['neighborhood'] = 'Centro'
            contact['address'] = ''
            
            contacts.append(contact)
    
    return contacts


def load_json_data() -> list:
    """
    Load and consolidate data from existing JSON files.
    Returns list of contacts from all JSON sources.
    """
    contacts = []
    
    # Load from datos_ybarlucea_20km.json
    json_file1 = SCRIPT_DIR / "datos_ybarlucea_20km.json"
    if json_file1.exists():
        try:
            with open(json_file1, 'r', encoding='utf-8') as f:
                data = json.load(f)
                contacts.extend(data.get('contacts', []))
                logger.info(f"Loaded {len(data.get('contacts', []))} contacts from datos_ybarlucea_20km.json")
        except Exception as e:
            logger.warning(f"Error loading {json_file1}: {e}")
    
    # Load from profesionales_ybarlucea.json
    json_file2 = SCRIPT_DIR / "profesionales_ybarlucea.json"
    if json_file2.exists():
        try:
            with open(json_file2, 'r', encoding='utf-8') as f:
                data = json.load(f)
                contacts.extend(data.get('contacts', []))
                logger.info(f"Loaded {len(data.get('contacts', []))} contacts from profesionales_ybarlucea.json")
        except Exception as e:
            logger.warning(f"Error loading {json_file2}: {e}")
    
    # Load from real_businesses_ybarlucea.json
    json_file3 = SCRIPT_DIR / "real_businesses_ybarlucea.json"
    if json_file3.exists():
        try:
            with open(json_file3, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # This file is a list, not a dict with metadata
                if isinstance(data, list):
                    contacts.extend(data)
                    logger.info(f"Loaded {len(data)} contacts from real_businesses_ybarlucea.json")
        except Exception as e:
            logger.warning(f"Error loading {json_file3}: {e}")
    
    return contacts


def filter_by_distance(contacts: list, max_km: float = MAX_DISTANCE_KM) -> list:
    """
    Filter contacts by distance from Ybarlucea center.
    Uses provided coordinates or defaults to Ybarlucea if missing.
    """
    filtered = []
    
    for contact in contacts:
        lat = contact.get('latitude', YBARLUCEA_LAT)
        lon = contact.get('longitude', YBARLUCEA_LON)
        
        # If no coordinates, assume it's in Ybarlucea (distance = 0)
        if lat is None or lon is None:
            lat = YBARLUCEA_LAT
            lon = YBARLUCEA_LON
            contact['latitude'] = lat
            contact['longitude'] = lon
            contact['distance_km'] = 0.0
        
        distance = haversine_distance(YBARLUCEA_LAT, YBARLUCEA_LON, lat, lon)
        contact['distance_km'] = round(distance, 2)
        
        if distance <= max_km:
            filtered.append(contact)
        else:
            logger.debug(f"Filtered out (distance {distance:.1f}km > {max_km}km): {contact.get('name')}")
    
    return filtered


def assign_default_city(contacts: list) -> list:
    """
    Assign default city (Ibarlucea) to contacts without a city.
    This ensures all contacts have a valid city.
    """
    default_city = 'Ibarlucea'
    default_neighborhood = 'Centro'
    
    for contact in contacts:
        city = contact.get('city', '').strip()
        if not city:
            # Check if there's any location info in the address
            address = contact.get('address', '').lower()
            
            # Check if it's clearly in another city
            if 'rosario' in address:
                contact['city'] = 'Rosario'
            elif 'funes' in address:
                contact['city'] = 'Funes'
            elif 'granadero baigorria' in address or 'baigorria' in address:
                contact['city'] = 'Granadero Baigorria'
            elif 'ybarlucea' in address:
                contact['city'] = 'Ybarlucea'
            elif 'ibarlucea' in address:
                contact['city'] = 'Ibarlucea'
            else:
                # Default to Ibarlucea
                contact['city'] = default_city
        
        # Ensure neighborhood exists
        neighborhood = contact.get('neighborhood', '').strip()
        if not neighborhood:
            contact['neighborhood'] = default_neighborhood
    
    return contacts


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number format.
    """
    if not phone:
        return ''
    
    # Remove extra spaces
    phone = re.sub(r'\s+', ' ', phone.strip())
    
    # Remove leading +54 or 0 if present
    phone = re.sub(r'^\+54\s*', '', phone)
    phone = re.sub(r'^0\s*', '', phone)
    
    return phone


def get_existing_contacts(cursor) -> set:
    """Get set of existing contact names for duplicate detection."""
    cursor.execute("SELECT LOWER(name), LOWER(COALESCE(address, '')) FROM contacts")
    return set((row[0], row[1]) for row in cursor.fetchall())


def import_contacts_to_db(contacts: list, db_path: Path, user_id: int = 1) -> dict:
    """
    Import contacts to database.
    Returns statistics about the import.
    """
    stats = {
        'total_in_list': len(contacts),
        'inserted': 0,
        'skipped_duplicates': 0,
        'skipped_no_name': 0,
        'errors': 0,
        'by_category': {}
    }
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get existing contacts
        existing = get_existing_contacts(cursor)
        logger.info(f"Found {len(existing)} existing contacts in database")
        
        for contact in contacts:
            try:
                name = contact.get('name', '').strip()
                
                if not name:
                    stats['skipped_no_name'] += 1
                    continue
                
                # Get address for duplicate check
                address = contact.get('address', '').strip()
                
                # Check for duplicate by name + address
                if (name.lower(), address.lower()) in existing:
                    stats['skipped_duplicates'] += 1
                    logger.debug(f"Skipping duplicate: {name}")
                    continue
                
                # Get category_id and map to database ID
                old_cat_id = contact.get('category_id', 999)
                
                # Map old category codes to database IDs
                if 100 <= old_cat_id <= 123:
                    category_id = old_cat_id - 99  # 100 -> 1, 101 -> 2, etc.
                elif old_cat_id == 999:
                    category_id = 26  # "Otro" category
                else:
                    category_id = 26  # Default to "Otro"
                
                # Get values
                phone = normalize_phone(contact.get('phone', ''))
                email = contact.get('email', '').strip() or ''
                city = contact.get('city', 'Ibarlucea').strip() or 'Ibarlucea'
                neighborhood = contact.get('neighborhood', 'Centro').strip() or 'Centro'
                description = contact.get('description', '').strip() or ''
                schedule = contact.get('schedule', '').strip() or ''
                latitude = contact.get('latitude')
                longitude = contact.get('longitude')
                distance_km = contact.get('distance_km', 0)
                verification_level = contact.get('verification_level', 1)
                source = contact.get('source', 'imported')
                
                # Add source info to description
                if source and 'vcf:' in source:
                    description = f"[{source}] {description}" if description else f"[{source}]"
                elif source:
                    description = f"[Fuente: {source}] {description}" if description else f"[Fuente: {source}]"
                
                # Insert new contact
                cursor.execute("""
                    INSERT INTO contacts (
                        name, phone, email, address, city, neighborhood, 
                        category_id, description, schedule, 
                        latitude, longitude, status, verification_level,
                        user_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name,
                    phone,
                    email,
                    address,
                    city,
                    neighborhood,
                    category_id,
                    description,
                    schedule,
                    latitude,
                    longitude,
                    'active',
                    verification_level,
                    user_id,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                
                stats['inserted'] += 1
                
                # Track by category
                cat_key = str(category_id)
                stats['by_category'][cat_key] = stats['by_category'].get(cat_key, 0) + 1
                
                existing.add((name.lower(), address.lower()))
                logger.info(f"Inserted: {name} ({city}) - Dist: {distance_km}km")
                
            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Error inserting contact '{contact.get('name', 'UNKNOWN')}': {e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Import complete: {stats['inserted']} inserted, {stats['skipped_duplicates']} duplicates skipped, {stats['errors']} errors")
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.close()
        raise
    
    return stats


def print_summary(contacts: list, stats: dict):
    """Print a summary of the import operation."""
    print("\n" + "="*70)
    print("IMPORTACION DE DATOS - ZONA YBARLUCEA (20km)")
    print("="*70)
    
    print(f"\nCentro de referencia: Ybarlucea")
    print(f"   Coordenadas: {YBARLUCEA_LAT}, {YBARLUCEA_LON}")
    print(f"   Radio maximo: {MAX_DISTANCE_KM} km")
    
    print("\n" + "-"*70)
    print("FUENTES DE DATOS:")
    print("-"*70)
    print(f"   - Archivos VCF: ~189 contactos")
    print(f"   - datos_ybarlucea_20km.json: ~85 contactos")
    print(f"   - profesionales_ybarlucea.json: ~28 contactos")
    print(f"   - real_businesses_ybarlucea.json: ~47 contactos")
    
    print("\n" + "-"*70)
    print("RESULTADOS DE IMPORTACION:")
    print("-"*70)
    print(f"   Contactos procesados:       {stats['total_in_list']}")
    print(f"   Insertados nuevos:         {stats['inserted']}")
    print(f"   Duplicados omitidos:       {stats['skipped_duplicates']}")
    print(f"   Sin nombre (omitidos):     {stats['skipped_no_name']}")
    print(f"   Errores:                  {stats['errors']}")
    
    if stats['by_category']:
        print("\n" + "-"*70)
        print("POR CATEGORÍA:")
        print("-"*70)
        
        # Category names mapping (old codes)
        cat_names = {
            '1': 'Plomero/a',
            '2': 'Gasista',
            '3': 'Electricista',
            '4': 'Peluquería/Barbería',
            '5': 'Albañil',
            '6': 'Pintor',
            '7': 'Carpintero/a',
            '8': 'Supermercado',
            '9': 'Carnicería',
            '10': 'Verdulería',
            '11': 'Panadería',
            '12': 'Tienda de ropa',
            '13': 'Farmacia',
            '14': 'Librería',
            '15': 'Bar',
            '16': 'Restaurant',
            '17': 'Club',
            '18': 'Bazar',
            '19': 'Veterinaria',
            '20': 'Ferretería',
            '21': 'Kiosco',
            '22': 'Juguetería',
            '23': 'Polirrubro',
            '24': 'Cuidado de personas',
            '25': 'Alquiler',
            '26': 'Otro'
        }
        
        for cat_id, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
            cat_name = cat_names.get(cat_id, f'Categoría {cat_id}')
            print(f"   {cat_name:30s}: {count:3d}")


def main():
    """Main function to run the consolidation and import."""
    print("\n>>> Iniciando consolidacion e importacion de datos...\n")
    
    # Step 1: Parse VCF files
    print("[1] Parseando archivos VCF...")
    vcf_contacts = parse_all_vcf_files()
    print(f"    -> {len(vcf_contacts)} contactos extraidos de VCF")
    
    # Step 2: Load JSON data
    print("\n[2] Cargando datos de archivos JSON...")
    json_contacts = load_json_data()
    print(f"    -> {len(json_contacts)} contactos cargados de JSON")
    
    # Step 3: Combine all contacts
    print("\n[3] Combinando todas las fuentes...")
    all_contacts = vcf_contacts + json_contacts
    print(f"    -> Total combinados: {len(all_contacts)} contactos")
    
    # Step 4: Filter by distance
    print(f"\n[4] Filtrando por distancia maxima de {MAX_DISTANCE_KM}km...")
    filtered_contacts = filter_by_distance(all_contacts, MAX_DISTANCE_KM)
    print(f"    -> Contactos dentro del radio: {len(filtered_contacts)}")
    
    # Step 5: Assign default city
    print("\n[5] Asignando ciudad por defecto a contactos sin zona...")
    final_contacts = assign_default_city(filtered_contacts)
    cities_count = {}
    for c in final_contacts:
        city = c.get('city', 'Unknown')
        cities_count[city] = cities_count.get(city, 0) + 1
    print(f"    -> Distribucion por ciudad:")
    for city, count in sorted(cities_count.items(), key=lambda x: -x[1]):
        print(f"       - {city}: {count}")
    
    # Step 6: Save consolidated JSON
    print("\n[6] Guardando JSON consolidado...")
    try:
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'zone': 'Ybarlucea (Ibarlucea) y alrededores',
                    'radius_km': MAX_DISTANCE_KM,
                    'center': {'latitude': YBARLUCEA_LAT, 'longitude': YBARLUCEA_LON},
                    'date_generated': datetime.now().isoformat(),
                    'total_contacts': len(final_contacts)
                },
                'contacts': final_contacts
            }, f, ensure_ascii=False, indent=2)
        print(f"    -> Guardado en: {OUTPUT_JSON}")
    except Exception as e:
        print(f"    ! Error al guardar JSON: {e}")
    
    # Step 7: Import to database
    print("\n[7] Importando a la base de datos...")
    try:
        stats = import_contacts_to_db(final_contacts, DB_PATH)
    except Exception as e:
        print(f"    ERROR: Error al importar: {e}")
        return
    
    # Step 8: Print summary
    print_summary(final_contacts, stats)
    
    print("\n" + "="*70)
    print("IMPORTACION COMPLETADA!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
