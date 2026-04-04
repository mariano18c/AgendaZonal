import json
import sqlite3

# Load consolidated contacts
with open(r'C:\Users\maria\Proyectos\AgendaZonal\backend\fuente_datos\consolidated_contacts.json', encoding='utf-8') as f:
    data = json.load(f)

contacts = data.get('contacts', [])
print(f"=== ANALISIS DE CONTACTS CONSOLIDADOS ===")
print(f"Total en archivo: {len(contacts)}")

# Filter contacts that come from VCF (local contacts that might not be in DB)
vcf_contacts = [c for c in contacts if 'vcf' in c.get('source', '').lower()]
print(f"\nContactos de archivos VCF: {len(vcf_contacts)}")

# Get contacts with phone numbers
contacts_with_phone = [c for c in vcf_contacts if c.get('phone')]
print(f"Contactos VCF con teléfono: {len(contacts_with_phone)}")

# Connect to database
DB_PATH = r'C:\Users\maria\Proyectos\AgendaZonal\backend\database\agenda.db'
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get existing phone numbers from database
cursor.execute("SELECT phone FROM contacts WHERE phone != ''")
existing_phones = set(row[0] for row in cursor.fetchall())
print(f"\nTeléfonos en base de datos: {len(existing_phones)}")

# Find new contacts (VCF with phone that are NOT in DB)
new_contacts = []
for c in contacts_with_phone:
    phone = c.get('phone', '')
    # Extract clean phone number
    if ':' in phone:
        phone_clean = phone.split(':')[1].replace('+54 9 ', '').replace('-', '').strip()
    else:
        phone_clean = phone.replace('+54 9 ', '').replace('-', '').strip()
    
    # Check if phone exists in DB
    if phone_clean not in existing_phones:
        new_contacts.append(c)

print(f"\n=== CONTACTOS VCF NUEVOS (no en DB) ===")
print(f"Total nuevos: {len(new_contacts)}")

# Show first 30 new contacts
print("\nPrimeros 30 contactos nuevos:")
for i, c in enumerate(new_contacts[:30], 1):
    name = c.get('name', 'N/A')
    phone = c.get('phone', 'N/A')[:30]
    city = c.get('city', 'N/A')
    category = c.get('category_id', 999)
    print(f"{i}. {name} | {phone} | {city} | Cat: {category}")

# Check categories distribution of new contacts
print(f"\n=== CATEGORIAS DE NUEVOS CONTACTOS ===")
categories = {}
for c in new_contacts:
    cat = c.get('category_id', 999)
    if cat is None:
        cat = 999
    categories[cat] = categories.get(cat, 0) + 1
for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
    print(f"Categoría {cat}: {count}")

conn.close()