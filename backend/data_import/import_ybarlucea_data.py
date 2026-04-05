#!/usr/bin/env python3
"""
Script to import collected Ybarlucea area business data into the database.
This script loads data from datos_ybarlucea_20km.json and inserts it into the database.

Usage:
    python import_ybarlucea_data.py

The script will:
1. Load the JSON data file
2. Connect to the database
3. Insert new contacts (skipping duplicates)
4. Report statistics
"""

import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "datos_ybarlucea_20km.json"
DB_PATH = SCRIPT_DIR.parent / "database" / "agenda.db"


def load_json_data() -> dict:
    """Load the collected business data from JSON file."""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data.get('contacts', []))} contacts from {DATA_FILE}")
        return data
    except FileNotFoundError:
        logger.error(f"Data file not found: {DATA_FILE}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in data file: {e}")
        raise


def get_existing_contacts(cursor) -> set:
    """Get set of existing contact names and addresses for duplicate detection."""
    cursor.execute("SELECT LOWER(name), LOWER(address) FROM contacts")
    return set((row[0], row[1]) for row in cursor.fetchall())


def import_contacts(data: dict, db_path: Path, user_id: int = 1) -> dict:
    """
    Import contacts from the data dictionary into the database.
    Returns statistics about the import operation.
    """
    contacts = data.get('contacts', [])
    metadata = data.get('metadata', {})
    
    stats = {
        'total_in_file': len(contacts),
        'inserted': 0,
        'skipped_duplicates': 0,
        'errors': 0,
        'by_category': {}
    }
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get existing contacts to avoid duplicates
        existing = get_existing_contacts(cursor)
        logger.info(f"Found {len(existing)} existing contacts in database")
        
        # Get category mapping (code -> id)
        cursor.execute("SELECT code, id FROM categories")
        category_map = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Mapping from our category_id (old codes) to new category IDs
        # Old codes: 100-122, 999
        # New system: same codes stored in category.code
        old_to_new_cat = {}
        for old_id in range(100, 123):
            old_to_new_cat[old_id] = old_id
        old_to_new_cat[999] = 999  # Otro
        
        for contact in contacts:
            try:
                name = contact.get('name', '').strip()
                address = contact.get('address', '').strip()
                city = contact.get('city', '').strip()
                
                # Skip if missing essential info (name is required, but address can be derived from city)
                if not name:
                    stats['errors'] += 1
                    logger.warning(f"Skipping contact with missing name")
                    continue
                
                # Use city as address if address is empty
                if not address and city:
                    address = city
                
                # Check for duplicate
                if (name.lower(), address.lower()) in existing:
                    stats['skipped_duplicates'] += 1
                    logger.debug(f"Skipping duplicate: {name}")
                    continue
                
                # Map category_id from old system to database IDs
                # Database uses: code 100-123 -> id 1-24, code 999 -> id 26
                old_cat_id = contact.get('category_id', 999)
                
                # Map old category codes to database IDs
                if 100 <= old_cat_id <= 123:
                    category_id = old_cat_id - 99  # 100 -> 1, 101 -> 2, etc.
                elif old_cat_id == 999:
                    category_id = 26  # "Otro" category
                else:
                    category_id = 26  # Default to "Otro"
                
                # Get values from contact
                phone = contact.get('phone', '').strip() or ''
                email = contact.get('email', '').strip() or ''
                city = contact.get('city', 'Ibarlucea').strip() or 'Ibarlucea'
                neighborhood = contact.get('neighborhood', 'Centro').strip() or 'Centro'
                description = contact.get('description', '').strip() or ''
                schedule = contact.get('schedule', '').strip() or ''
                latitude = contact.get('latitude')
                longitude = contact.get('longitude')
                verification_level = contact.get('verification_level', 1)
                
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
                logger.info(f"Inserted: {name} ({city})")
                
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


def print_summary(data: dict, stats: dict):
    """Print a summary of the import operation."""
    print("\n" + "="*60)
    print("IMPORTACION DE DATOS - ZONA YBARLUCEA (20km)")
    print("="*60)
    
    metadata = data.get('metadata', {})
    print(f"\nZona: {metadata.get('zone', 'N/A')}")
    print(f"Radio: {metadata.get('radius_km', 'N/A')} km")
    print(f"Fecha de recoleccion: {metadata.get('date_collected', 'N/A')}")
    print(f"Fuentes consultadas: {len(metadata.get('sources', []))}")
    
    print("\n" + "-"*60)
    print("RESULTADOS DE IMPORTACION:")
    print("-"*60)
    print(f"   Contactos en archivo:    {stats['total_in_file']}")
    print(f"   Insertados nuevos:        {stats['inserted']}")
    print(f"   Duplicados omitidos:     {stats['skipped_duplicates']}")
    print(f"   Errores:                 {stats['errors']}")
    
    if stats['by_category']:
        print("\n" + "-"*60)
        print("POR CATEGORÍA:")
        print("-"*60)
        
        # Category names mapping
        cat_names = {
            '100': 'Plomero/a',
            '101': 'Gasista',
            '102': 'Electricista',
            '103': 'Peluquería/Barbería',
            '104': 'Albañil',
            '105': 'Pintor',
            '106': 'Carpintero/a',
            '107': 'Supermercado',
            '108': 'Carnicería',
            '109': 'Verdulería',
            '110': 'Panadería',
            '111': 'Tienda de ropa',
            '112': 'Farmacia',
            '113': 'Librería',
            '114': 'Bar',
            '115': 'Restaurant',
            '116': 'Club',
            '117': 'Bazar',
            '118': 'Veterinaria',
            '119': 'Ferretería',
            '120': 'Kiosco',
            '121': 'Juguetería',
            '122': 'Polirrubro',
            '999': 'Otro'
        }
        
        for cat_id, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
            cat_name = cat_names.get(cat_id, f'Categoría {cat_id}')
            print(f"  {cat_name:30s}: {count:3d}")


def main():
    """Main function to run the import."""
    print("\n>>> Iniciando importacion de datos de Ybarlucea y alrededores...\n")
    
    # Check if data file exists
    if not DATA_FILE.exists():
        print(f"❌ Error: No se encontró el archivo de datos: {DATA_FILE}")
        return
    
    # Load JSON data
    try:
        data = load_json_data()
    except Exception as e:
        print(f"❌ Error al cargar datos: {e}")
        return
    
    # Import to database
    try:
        stats = import_contacts(data, DB_PATH)
    except Exception as e:
        print(f"❌ Error al importar a la base de datos: {e}")
        return
    
    # Print summary
    print_summary(data, stats)
    
    print("\n" + "="*60)
    print("IMPORTACION COMPLETADA!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
