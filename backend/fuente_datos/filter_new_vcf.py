import json
import sqlite3

# Load consolidated contacts
with open(r'C:\Users\maria\Proyectos\AgendaZonal\backend\fuente_datos\consolidated_contacts.json', encoding='utf-8') as f:
    data = json.load(f)

contacts = data.get('contacts', [])

# Filter contacts from VCF files only
vcf_contacts = [c for c in contacts if 'vcf' in c.get('source', '').lower()]

# Get existing from database
DB_PATH = r'C:\Users\maria\Proyectos\AgendaZonal\backend\database\agenda.db'
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get existing contacts from database
cursor.execute("SELECT LOWER(name), phone FROM contacts")
existing = set()
for row in cursor.fetchall():
    name, phone = row
    existing.add((name, phone))

print("Total VCF:", len(vcf_contacts))
print("Ya en DB:", len(existing))

# Find truly NEW contacts
truly_new = []
for c in vcf_contacts:
    name = c.get('name', '').strip()
    phone_raw = c.get('phone', '')
    
    # Skip invalid names
    if not name or name == 'VCARD' or name.startswith('+549') or len(name) < 3:
        continue
    
    # Extract clean phone
    if ':' in phone_raw:
        phone = phone_raw.split(':')[1].strip()
    else:
        phone = phone_raw.strip()
    
    # Check if name exists in DB
    if (name.lower(), '') not in existing and (name.lower(), phone) not in existing:
        truly_new.append({
            'name': name,
            'phone': phone,
            'city': c.get('city', 'Ibarlucea'),
            'category_id': c.get('category_id', 999),
            'address': c.get('address', ''),
            'source': 'VCF local'
        })

print("Contactos nuevos:", len(truly_new))

# Save to file
output = {
    "metadata": {
        "zone": "Ybarlucea - Contactos VCF locales",
        "source": "Archivos VCF locales",
        "date_collected": "2026-03-31",
        "total_contacts": len(truly_new)
    },
    "contacts": truly_new
}

with open(r'C:\Users\maria\Proyectos\AgendaZonal\backend\fuente_datos\vcf_nuevos.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("Guardado: vcf_nuevos.json")
conn.close()