import json

# Load consolidated contacts
with open(r'C:\Users\maria\Proyectos\AgendaZonal\backend\fuente_datos\consolidated_contacts.json', encoding='utf-8') as f:
    data = json.load(f)

contacts = data.get('contacts', [])
print(f"=== CONSOLIDATED CONTACTS ===")
print(f"Total en archivo: {len(contacts)}")
print(f"\nPrimeros 30 contactos:")
for i, c in enumerate(contacts[:30], 1):
    name = c.get('name', 'N/A')
    phone = c.get('phone', 'N/A')
    city = c.get('city', 'N/A')
    category = c.get('category_id', 'N/A')
    source = c.get('source', 'N/A')
    print(f"{i}. {name} | {phone} | {city} | Cat: {category}")
    print(f"   Source: {source[:50]}..." if len(source) > 50 else f"   Source: {source}")

print(f"\n\n=== ULTIMOS 10 CONTACTOS ===")
for i, c in enumerate(contacts[-10:], len(contacts)-9):
    name = c.get('name', 'N/A')
    phone = c.get('phone', 'N/A')
    city = c.get('city', 'N/A')
    print(f"{i}. {name} | {phone} | {city}")

# Check unique cities
print(f"\n=== CIUDADES ===")
cities = {}
for c in contacts:
    city = c.get('city', 'None')
    cities[city] = cities.get(city, 0) + 1
for city, count in sorted(cities.items(), key=lambda x: -x[1]):
    print(f"{city}: {count}")

# Check unique sources
print(f"\n=== FUENTES ===")
sources = {}
for c in contacts:
    source = c.get('source', 'None')
    # Extract file extension or type
    if 'vcf' in source:
        src = 'vcf'
    elif '.json' in source:
        src = 'json'
    else:
        src = source[:30]
    sources[src] = sources.get(src, 0) + 1
for src, count in sorted(sources.items(), key=lambda x: -x[1])[:20]:
    print(f"{src}: {count}")