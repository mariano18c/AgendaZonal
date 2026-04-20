import os

file_path = 'frontend/search.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add aria-label to search input
input_target = '<input\n          type="text"\n          id="searchInput"'
input_replacement = '<input\n          type="text"\n          id="searchInput"\n          aria-label="Buscar contactos por nombre, teléfono o ciudad"'

# 2. Add focus management after map init
map_target = "map = window.L.map('searchMap').setView([-32.862574, -60.759585], 12);"
map_replacement = """map = window.L.map('searchMap').setView([-32.862574, -60.759585], 12);
          if (typeof setupAccessibilityFocusManagement === 'function') {
            setupAccessibilityFocusManagement(map);
          }"""

updated = False

if input_target in content:
    content = content.replace(input_target, input_replacement)
    updated = True

if map_target in content:
    content = content.replace(map_target, map_replacement)
    updated = True

if updated:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully updated search.html")
else:
    print("No targets found in search.html")
    # Debugging
    print(f"Target in content? {map_target in content}")
