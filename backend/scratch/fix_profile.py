import os

file_path = 'frontend/profile.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = '            L.marker([contact.latitude, contact.longitude]).addTo(miniMap).bindPopup(s(contact.name));'
replacement = """            const marker = L.marker([contact.latitude, contact.longitude], {
              title: contact.name,
              alt: `Marcador de ${contact.name}`
            }).addTo(miniMap).bindPopup(s(contact.name));
            
            marker.on('add', () => {
              const el = marker.getElement();
              if (el) {
                el.setAttribute('role', 'button');
                el.setAttribute('aria-label', `Marcador de ${contact.name}. Presiona para ver detalles.`);
              }
            });"""

if target in content:
    new_content = content.replace(target, replacement)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully updated profile.html")
else:
    print("Target content not found in profile.html")
