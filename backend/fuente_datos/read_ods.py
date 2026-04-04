import zipfile
import xml.etree.ElementTree as ET
import json

# Read ODS file
ods_path = r'C:\Users\maria\Proyectos\AgendaZonal\backend\fuente_datos\contactos.ods'

with zipfile.ZipFile(ods_path, 'r') as z:
    content = z.read('content.xml')

# Parse XML
root = ET.fromstring(content)

# Define namespaces
namespaces = {
    'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
    'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'
}

def get_cell_text(cell):
    """Extract text from a table cell"""
    text_elems = cell.findall('.//text:p', namespaces)
    text = ' '.join([t.text or '' for t in text_elems])
    return text.strip()

# Find all tables
tables = root.findall('.//table:table', namespaces)

contacts = []

# Process Hoja1 - main contacts
table1 = tables[0]
rows1 = table1.findall('.//table:table-row', namespaces)

# Get headers
header_row = rows1[0]
headers = []
for cell in header_row.findall('table:table-cell', namespaces):
    headers.append(get_cell_text(cell))

print(f"Headers: {headers}")

# Process data rows (skip header)
for row in rows1[1:]:
    cells = row.findall('table:table-cell', namespaces)
    if len(cells) >= 3:
        category = get_cell_text(cells[0])
        name = get_cell_text(cells[1])
        phone = get_cell_text(cells[2])
        details = get_cell_text(cells[3]) if len(cells) > 3 else ""
        
        if name and phone:
            # Map category to category_id
            cat_map = {
                'Transporte (Remis)': 122,
                'Gasista y Plomería': 101,
                'Plomero y Gasista': 100,
                'Climatización y Línea Blanca': 999,
                'Mantenimiento Integral': 100,
                'Reparación Técnica': 999,
                'Eventos y Entretenimiento': 114,
                'Venta de Leña': 122,
                'Servicios Legales': 999,
            }
            category_id = cat_map.get(category, 999)
            
            contacts.append({
                'name': name,
                'phone': phone,
                'address': 'Ibarlucea, Santa Fe',
                'city': 'Ibarlucea',
                'neighborhood': 'Centro',
                'category_id': category_id,
                'description': details[:200] if details else category,
                'schedule': '',
                'latitude': -32.8833,
                'longitude': -60.7833,
                'distance_km': 0.0,
                'verification_level': 2,
                'source': 'contactos.ods - Hoja1'
            })

print(f"\nContactos de Hoja1: {len(contacts)}")

# Process Hoja2 - Farmacias
table2 = tables[1]
rows2 = table2.findall('.//table:table-row', namespaces)

# Get headers
header_row2 = rows2[0]
headers2 = []
for cell in header_row2.findall('table:table-cell', namespaces):
    headers2.append(get_cell_text(cell))

print(f"Headers Hoja2: {headers2}")

# Process data rows (skip header)
for row in rows2[1:]:
    cells = row.findall('table:table-cell', namespaces)
    if len(cells) >= 4:
        day = get_cell_text(cells[0])
        pharmacy = get_cell_text(cells[1])
        address = get_cell_text(cells[2])
        phone = get_cell_text(cells[3])
        
        if pharmacy:
            contacts.append({
                'name': f"Farmacia {pharmacy}",
                'phone': phone,
                'address': address,
                'city': 'Granadero Baigorria',
                'neighborhood': 'Centro',
                'category_id': 12,  # Farmacia
                'description': f"Farmacia de turno los días {day}",
                'schedule': f"Días {day}",
                'latitude': -32.855,
                'longitude': -60.72,
                'distance_km': 6.0,
                'verification_level': 2,
                'source': 'contactos.ods - Hoja2'
            })

print(f"Total contactos: {len(contacts)}")

# Save to JSON
output = {
    "metadata": {
        "zone": "Ybarlucea - Archivo ODS contactos",
        "source": "contactos.ods",
        "date_collected": "2026-03-31",
        "total_contacts": len(contacts),
        "description": "Datos locales de la zona extraídos de archivo ODS"
    },
    "contacts": contacts
}

with open(r'C:\Users\maria\Proyectos\AgendaZonal\backend\fuente_datos\contactos_ods.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✅ Guardado: contactos_ods.json ({len(contacts)} contactos)")

# Show sample
print("\n=== Primeros 10 contactos ===")
for i, c in enumerate(contacts[:10], 1):
    print(f"{i}. {c['name'][:30]:30s} | {c['phone'][:15]:15s} | Cat: {c['category_id']}")