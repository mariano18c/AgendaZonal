/**
 * Geo utilities for AgendaZonal.
 * - getUserLocation(): Promise-based geolocation
 * - initMap(): Initialize Leaflet map
 * - addContactMarkers(): Add contact markers to map
 * - haversineDistance(): Client-side distance calculation (for display only)
 */

// ---------------------------------------------------------------------------
// Geolocation
// ---------------------------------------------------------------------------

/**
 * Get user's current position via browser geolocation API.
 * @returns {Promise<{lat: number, lon: number}>}
 */
function getUserLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Tu navegador no soporta geolocalización'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      (err) => {
        switch (err.code) {
          case 1: reject(new Error('Permiso de ubicación denegado'));
          case 2: reject(new Error('No se pudo obtener la ubicación'));
          case 3: reject(new Error('Tiempo de espera agotado'));
          default: reject(new Error('Error de geolocalización'));
        }
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
    );
  });
}

// ---------------------------------------------------------------------------
// Haversine (client-side, for display only — server does the real filtering)
// ---------------------------------------------------------------------------

function haversineDistance(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// ---------------------------------------------------------------------------
// Leaflet Map
// ---------------------------------------------------------------------------

/**
 * Initialize a Leaflet map in the given container.
 * @param {string} containerId - DOM element id
 * @param {number} lat - Center latitude
 * @param {number} lon - Center longitude
 * @param {number} zoom - Zoom level (default 13)
 * @returns {L.Map}
 */
function initMap(containerId, lat, lon, zoom = 13) {
  const map = L.map(containerId).setView([lat, lon], zoom);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(map);
  return map;
}

/**
 * Add a marker for the user's current location.
 * @param {L.Map} map
 * @param {number} lat
 * @param {number} lon
 */
function addUserLocationMarker(map, lat, lon) {
  const userIcon = L.divIcon({
    html: '<div style="background:#3b82f6;width:16px;height:16px;border-radius:50%;border:3px solid white;box-shadow:0 0 6px rgba(0,0,0,0.3);"></div>',
    className: '',
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
  return L.marker([lat, lon], { icon: userIcon }).addTo(map).bindPopup('Tu ubicación');
}

/**
 * Add a circle showing the search radius.
 * @param {L.Map} map
 * @param {number} lat
 * @param {number} lon
 * @param {number} radiusKm
 */
function addRadiusCircle(map, lat, lon, radiusKm) {
  return L.circle([lat, lon], {
    radius: radiusKm * 1000,
    color: '#3b82f6',
    fillColor: '#3b82f6',
    fillOpacity: 0.08,
    weight: 1,
  }).addTo(map);
}

/**
 * Create popup HTML for a contact marker.
 * @param {object} contact
 * @returns {string}
 */
function createContactPopup(contact) {
  const safe = (v) => {
    if (!v) return '';
    const d = document.createElement('div');
    d.textContent = v;
    return d.innerHTML;
  };
  let html = `<div style="min-width:180px">`;
  html += `<div style="font-weight:600;font-size:14px;">${safe(contact.name)}</div>`;
  if (contact.avg_rating > 0) {
    html += `<div style="color:#f59e0b;font-size:12px;">${'★'.repeat(Math.round(contact.avg_rating))} ${contact.avg_rating.toFixed(1)}</div>`;
  }
  if (contact.city) {
    html += `<div style="color:#6b7280;font-size:12px;">📍 ${safe(contact.city)}</div>`;
  }
  if (contact.distance_km != null) {
    html += `<div style="color:#6b7280;font-size:12px;">📏 ${contact.distance_km} km</div>`;
  }
  html += `<div style="margin-top:6px;"><a href="/search?contact=${contact.id}" style="color:#2563eb;font-size:13px;">Ver detalle →</a></div>`;
  if (contact.phone) {
    html += `<div><a href="tel:${safe(contact.phone)}" style="color:#2563eb;font-size:13px;">📞 Llamar</a></div>`;
  }
  html += `</div>`;
  return html;
}

/**
 * Add contact markers to the map.
 * @param {L.Map} map
 * @param {Array} contacts - Array of contact objects with lat/lng
 * @returns {L.LayerGroup}
 */
function addContactMarkers(map, contacts) {
  if (window._contactMarkers) {
    map.removeLayer(window._contactMarkers);
  }
  const markers = [];
  contacts.forEach(c => {
    if (c.latitude && c.longitude) {
      const marker = L.marker([c.latitude, c.longitude])
        .bindPopup(createContactPopup(c), { maxWidth: 250 });
      markers.push(marker);
    }
  });
  window._contactMarkers = L.markerClusterGroup();
  window._contactMarkers.addLayers(markers);
  map.addLayer(window._contactMarkers);
  return window._contactMarkers;
}

/**
 * Fit map bounds to show all markers.
 * @param {L.Map} map
 * @param {Array} contacts
 */
function fitMapToContacts(map, contacts) {
  const coords = contacts
    .filter(c => c.latitude && c.longitude)
    .map(c => [c.latitude, c.longitude]);
  if (coords.length > 0) {
    map.fitBounds(coords, { padding: [30, 30], maxZoom: 15 });
  }
}
