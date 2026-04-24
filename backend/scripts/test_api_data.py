import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def test_api():
    print("--- 1. Listando primeros 5 contactos ---")
    r = requests.get(f"{BASE_URL}/contacts?limit=5")
    if r.status_code == 200:
        data = r.json()
        for c in data["contacts"]:
            print(f"[{c['id']}] {c['name']} - Cat: {c['category_id']} - Status: {c['status']}")
    
    print("\n--- 2. Buscando 'Comuna' (Enriquecida) ---")
    r = requests.get(f"{BASE_URL}/contacts/search?q=Comuna")
    if r.status_code == 200:
        data = r.json()
        for c in data["contacts"]:
            print(f"Name: {c['name']} | Phone: {c['phone']} | Desc: {c['description'][:100]}...")

    print("\n--- 3. Buscando 'Remis' (Recategorizados) ---")
    r = requests.get(f"{BASE_URL}/contacts/search?q=Remis")
    if r.status_code == 200:
        data = r.json()
        for c in data["contacts"]:
            print(f"Name: {c['name']} | Cat: {c['category_id']} | Status: {c['status']}")

    print("\n--- 4. Conteo de contactos por estado ---")
    # No hay endpoint directo, pero podemos ver el total general
    r = requests.get(f"{BASE_URL}/contacts?limit=1")
    if r.status_code == 200:
        print(f"Total contactos activos: {r.json()['total']}")

if __name__ == "__main__":
    try:
        test_api()
    except Exception as e:
        print(f"Error calling API: {e}")
