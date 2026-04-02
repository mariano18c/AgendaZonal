# DESIGN-003: Evolución Hiperzonal — Diseño Técnico

## Metadata
- **Creado**: 2026-03-29
- **Autor**: MarianoC
- **Estado**: active
- **Basado en**: SPEC-003 | PROPOSAL-003

---

## Decisiones de Arquitectura

### AD-01: Geo Queries — SpatiaLite vs Haversine

**Decisión: Haversine en Python/SQL para MVP. SpatiaLite como mejora futura.**

| Factor | SpatiaLite | Haversine Python |
|--------|-----------|-----------------|
| Dependencia OS | `mod_spatialite` library | Ninguna |
| Deploy RPi | Requiere `apt install libsqlite3-mod-spatialite` | Funciona out-of-box |
| Precisión | Geodésica exacta | ~0.5% error (suficiente para <50km) |
| Performance | Índice R-Tree, <1ms para 10k rows | ~10ms para 500 rows (OK) |
| Escalabilidad | 100k+ proveedores | Hasta ~5k proveedores |
| Complejidad | Alta (extension loading, migration) | Baja (fórmula matemática) |

**Implementación Haversine:**
```python
# Formula Haversine en SQL (SQLite)
# distancia_km = 6371 * acos(cos(radians(lat1)) * cos(radians(lat2)) *
#               cos(radians(lon2) - radians(lon1)) + sin(radians(lat1)) * sin(radians(lat2)))

import math

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371  # Radio Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))
```

**Estrategia de query:**
1. Bounding box first (rápido, usa índices numéricos estándar)
2. Haversine refinamiento (precisión sobre subset pequeño)

```python
# Bounding box: ~1 grado ≈ 111km en el ecuador
lat_range = radius_km / 111.0
lon_range = radius_km / (111.0 * math.cos(math.radians(center_lat)))

# Query SQL con bounding box (usa índice en lat/lon)
query = query.filter(
    Contact.latitude >= center_lat - lat_range,
    Contact.latitude <= center_lat + lat_range,
    Contact.longitude >= center_lon - lon_range,
    Contact.longitude <= center_lon + lon_range,
)
```

### AD-02: Rating Promedio Cacheado vs Calculado

**Decisión: Cacheado en contacts.avg_rating + contacts.review_count.**

| Enfoque | Pros | Contras |
|---------|-----|---------|
| Calculado (query) | Siempre preciso | JOIN + AVG en cada lectura |
| Cacheado (columna) | Lectura instantánea | Requiere recálculo al cambiar reseñas |

Para un directorio donde las reseñas cambian poco y las lecturas son frecuentes, cacheado gana. Recálculo se hace al:
- Aprobar una reseña (`avg_rating = AVG(rating WHERE is_approved=true)`)
- Rechazar una reseña previamente aprobada

### AD-03: Estado de Contacto (Status)

**Decisión: Campo `status` en Contact con 3 valores.**

```
active    → visible normalmente
flagged   → visible pero con advertencia (3+ reportes)
suspended → NO visible en búsquedas (admin lo suspendió)
```

Migración de `is_verified` → `verification_level`:
- `is_verified=false` → `verification_level=0`
- `is_verified=true` → `verification_level=1` (mínimo)
- Admin puede subir a 2 o 3 manualmente

### AD-04: Sistema de Imágenes para Reseñas

**Decisión: Reutilizar el patrón existente de uploads de contactos.**

```
uploads/
  images/
    contact_{id}.jpg         ← ya existe
    review_{id}.jpg          ← nuevo, mismo directorio
```

Validaciones idénticas: JPEG, max 2MB (menor que contactos), resize a 800x800.

### AD-05: Service Worker Strategy

**Decisión: Network-first con fallback a cache.**

```
1. Buscar en red
2. Si OK → retornar + actualizar cache
3. Si falla → retornar de cache
4. Si no hay cache → página offline.html
```

Assets cacheados:
- HTML pages (todas)
- JS files (api.js, app.js)
- CDN assets NO se cachean (Tailwind, Leaflet) — el browser las cachea nativamente

### AD-06: Rate Limiting por Endpoint

```
Global:          60/minute por IP
Auth (login):    10/minute por IP
Auth (register): 5/minute por IP
Reseñas:         5/hour por usuario
Contactos (POST): 10/day por usuario
Search:          30/minute por IP
```

---

## Schema de Base de Datos

### Tablas Nuevas

```sql
-- FASE 2: Reseñas
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    comment TEXT CHECK(length(comment) <= 500),
    photo_path VARCHAR(500),
    is_approved BOOLEAN NOT NULL DEFAULT 0,
    approved_by INTEGER REFERENCES users(id),
    approved_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(contact_id, user_id)
);

CREATE INDEX idx_reviews_contact ON reviews(contact_id);
CREATE INDEX idx_reviews_approved ON reviews(is_approved);

-- FASE 3: Ofertas
CREATE TABLE offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description VARCHAR(500),
    discount_pct INTEGER CHECK(discount_pct >= 1 AND discount_pct <= 99),
    expires_at DATETIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_offers_contact ON offers(contact_id);
CREATE INDEX idx_offers_active ON offers(is_active, expires_at);

-- FASE 3: Tracking de Leads
CREATE TABLE lead_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    source VARCHAR(20) NOT NULL DEFAULT 'whatsapp',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_leads_contact ON lead_events(contact_id);
CREATE INDEX idx_leads_date ON lead_events(created_at);

-- FASE 5: Reportes
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    reason VARCHAR(20) NOT NULL CHECK(reason IN ('spam', 'falso', 'inapropiado', 'cerrado')),
    details TEXT,
    is_resolved BOOLEAN NOT NULL DEFAULT 0,
    resolved_by INTEGER REFERENCES users(id),
    resolved_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(contact_id, user_id)
);

CREATE INDEX idx_reports_contact ON reports(contact_id);
CREATE INDEX idx_reports_unresolved ON reports(is_resolved);

-- FASE 5: Utilidades Barrio
CREATE TABLE utility_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type VARCHAR(20) NOT NULL DEFAULT 'otro',
    name VARCHAR(200) NOT NULL,
    address VARCHAR(255),
    phone VARCHAR(20),
    schedule VARCHAR(200),
    lat FLOAT,
    lon FLOAT,
    city VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_utilities_type ON utility_items(type);
CREATE INDEX idx_utilities_active ON utility_items(is_active);
```

### Cambios a Tabla `contacts`

```sql
ALTER TABLE contacts ADD COLUMN avg_rating FLOAT DEFAULT 0;
ALTER TABLE contacts ADD COLUMN review_count INTEGER DEFAULT 0;
ALTER TABLE contacts ADD COLUMN verification_level INTEGER DEFAULT 0;
ALTER TABLE contacts ADD COLUMN status VARCHAR(20) DEFAULT 'active';

-- Migrar datos existentes
UPDATE contacts SET verification_level = 1 WHERE is_verified = 1;
UPDATE contacts SET status = 'active';

CREATE INDEX idx_contacts_status ON contacts(status);
CREATE INDEX idx_contacts_verification ON contacts(verification_level);
CREATE INDEX idx_contacts_geo ON contacts(latitude, longitude);
CREATE INDEX idx_contacts_rating ON contacts(avg_rating);
```

---

## Arquitectura de Módulos (Backend)

```
backend/app/
├── models/
│   ├── __init__.py          ← agregar imports nuevos
│   ├── user.py              (existente)
│   ├── category.py          (existente)
│   ├── contact.py           ← agregar avg_rating, review_count, verification_level, status
│   ├── contact_change.py    (existente)
│   ├── notification.py      (existente)
│   ├── review.py            ← NUEVO
│   ├── offer.py             ← NUEVO
│   ├── lead_event.py        ← NUEVO
│   ├── report.py            ← NUEVO
│   └── utility_item.py      ← NUEVO
│
├── routes/
│   ├── __init__.py          ← agregar imports nuevos
│   ├── auth.py              (existente)
│   ├── categories.py        (existente)
│   ├── contacts.py          ← MODIFICAR: search geo, leads, offers sub-routes
│   ├── users.py             (existente)
│   ├── notifications.py     (existente, ya creado)
│   ├── reviews.py           ← NUEVO
│   ├── offers.py            ← NUEVO
│   ├── admin.py             ← NUEVO: reports, analytics, utilities
│   └── provider.py          ← NUEVO: dashboard proveedor
│
├── schemas/
│   ├── __init__.py
│   ├── auth.py              (existente)
│   ├── category.py          (existente)
│   ├── contact.py           ← MODIFICAR: agregar nuevos campos a response
│   ├── review.py            ← NUEVO
│   ├── offer.py             ← NUEVO
│   ├── lead.py              ← NUEVO
│   ├── report.py            ← NUEVO
│   └── utility.py           ← NUEVO
│
├── geo.py                   ← NUEVO: utilidades Haversine
├── database.py              (existente)
├── config.py                (existente)
├── auth.py                  (existente)
├── rate_limit.py            (existente)
└── main.py                  ← MODIFICAR: incluir nuevos routers
```

---

## Detalle de Endpoints

### FASE 1: Geo Search

#### GET /api/contacts/search (modificado)
```
Params existentes: q, category_id, skip, limit
Params nuevos:     lat, lon, radius_km (default 10)

Lógica:
1. Si lat+lon presentes → bounding box query → Haversine filter → ordenar por distancia
2. Si solo q/category_id → comportamiento actual (LIKE search)
3. Combinación: aplicar ambos filtros

Response: ContactResponse + distance_km field
```

### FASE 2: Reseñas

#### POST /api/contacts/{id}/reviews
```
Auth: requerido
Body: { rating: 1-5, comment?: string(max 500), photo?: file }
Validaciones:
  - rating obligatorio, 1-5
  - Un usuario → una reseña por contacto (UNIQUE constraint)
  - is_approved = false por defecto
  - Si hay foto: JPEG, max 2MB, resize 800x800
Response: 201 + ReviewResponse
```

#### GET /api/contacts/{id}/reviews
```
Auth: no requerido
Params: skip, limit (default 20)
Filtro: is_approved = true
Orden: created_at DESC
Response: [ReviewResponse] + total count
```

#### POST /api/admin/reviews/{id}/approve
```
Auth: moderator/admin
Acción: is_approved=true, approved_by=user.id, approved_at=now()
Recalcula: contact.avg_rating, contact.review_count
Response: ReviewResponse
```

#### POST /api/admin/reviews/{id}/reject
```
Auth: moderator/admin
Body: { reason?: string }
Acción: is_approved=false (si estaba aprobada, recalcular stats)
Response: ReviewResponse
```

#### PUT /api/admin/contacts/{id}/verification
```
Auth: moderator/admin
Body: { verification_level: 0|1|2|3 }
Response: ContactResponse con nuevo verification_level
```

### FASE 3: WhatsApp + Ofertas + Dashboard

#### POST /api/contacts/{id}/leads
```
Auth: opcional (user_id nullable)
Body: { source: 'whatsapp' }
Acción: insert en lead_events
Response: 201
```

#### GET /api/contacts/{id}/leads
```
Auth: requerido (solo dueño del contacto)
Params: days (default 30)
Response: { total, by_source: {whatsapp: N}, by_day: [{date, count}] }
```

#### CRUD Ofertas (5 endpoints)
```
POST   /api/contacts/{id}/offers         → crear oferta
GET    /api/contacts/{id}/offers         → listar ofertas activas (público)
PUT    /api/contacts/{id}/offers/{oid}   → editar oferta (solo dueño)
DELETE /api/contacts/{id}/offers/{oid}   → eliminar oferta (solo dueño)

Ofertas expiradas se filtran automáticamente (expires_at > now() AND is_active=true)
```

#### GET /api/provider/dashboard
```
Auth: requerido
Logic: busca todos los contactos del usuario, agrega métricas
Response: {
  contacts: [{id, name, avg_rating, review_count}],
  total_leads_this_month: N,
  total_leads_last_month: N,
  active_offers_count: N,
  recent_reviews: [ReviewResponse],
  leads_by_week: [{week_start, count}]
}
```

### FASE 5: Admin Avanzado

#### POST /api/contacts/{id}/report
```
Auth: requerido
Body: { reason: 'spam'|'falso'|'inapropiado'|'cerrado', details?: string }
Validaciones: no puede reportarse a sí mismo, UNIQUE(contact_id, user_id)
Auto-flag: si count(reports DISTINCT user WHERE NOT resolved) >= 3 → contact.status='flagged'
Response: 201
```

#### GET /api/admin/reports/flagged
```
Auth: moderator/admin
Response: contacts con status='flagged' + report details
```

#### POST /api/admin/reports/{id}/resolve
```
Auth: moderator/admin
Body: { action: 'reactivate'|'suspend'|'delete' }
Acción: según action, cambia contact.status
Response: ContactResponse
```

#### GET /api/admin/analytics
```
Auth: moderator/admin
Params: zone (city/neighborhood), date_from, date_to
Response: {
  total_providers: N,
  active_providers: N,
  total_leads: N,
  avg_rating: X.X,
  total_reviews: N,
  top_categories: [{name, count}],
  leads_by_day: [{date, count}]
}
```

#### GET /api/admin/analytics/export
```
Auth: moderator/admin
Params: format=csv, zone, date_from, date_to
Response: CSV file download
```

#### CRUD Utilidades (4 endpoints)
```
POST   /api/admin/utilities     → crear utilidad (admin)
GET    /api/utilities            → listar activas (público)
PUT    /api/admin/utilities/{id} → editar (admin)
DELETE /api/admin/utilities/{id} → eliminar (admin)
```

---

## Frontend

### Páginas Modificadas

#### search.html
- Agregar botón "Usar mi ubicación" (geolocalización)
- Agregar input de radio (slider 5-50km)
- Toggle "Lista" / "Mapa"
- Mapa con Leaflet: contenedor `div#map`, markers de contactos
- Resultados muestran `distance_km` si geo activo

#### index.html (landing)
- Nueva sección "Utilidades del Barrio" debajo de categorías
- Muestra farmacias de turno, emergencias

### Páginas Nuevas

#### profile.html (/profile?id={id})
- Info completa del proveedor
- Mapa mini con ubicación
- Rating con estrellas (promedio + cantidad)
- Lista de reseñas con paginación
- Formulario para crear reseña (si auth)
- Botón "Contactar por WhatsApp" (track + deep link)
- Ofertas activas con countdown
- Badge de verificación nivel 1/2/3

#### dashboard.html (/dashboard)
- Solo accesible si usuario tiene contactos
- Tarjetas de métricas: leads mes, rating, reseñas, ofertas
- Gráfico leads por semana (Chart.js desde CDN o SVG simple)
- Lista reseñas recientes

#### admin-reviews.html (/admin/reviews)
- Lista de reseñas pendientes
- Botones Aprobar / Rechazar
- Filtros: todas, pendientes, aprobadas

#### admin-reports.html (/admin/reports)
- Lista de proveedores flagged
- Detalle de reportes por proveedor
- Acciones: reactivar, suspender, eliminar

#### admin-analytics.html (/admin/analytics)
- Dashboard con métricas
- Filtros por zona y fecha
- Botón exportar CSV

#### admin-utilities.html (/admin/utilities)
- CRUD de utilidades barrio
- Formulario con mapa para ubicación

---

## Archivos JS

### js/api.js (modificar)
Agregar métodos:
```javascript
// Geo search
searchContactsGeo(query, categoryId, lat, lon, radiusKm, skip, limit)

// Reviews
getContactReviews(contactId, skip, limit)
createReview(contactId, rating, comment, photoFile)
approveReview(reviewId)
rejectReview(reviewId, reason)

// Leads
registerLead(contactId, source)
getContactLeads(contactId, days)

// Offers
getContactOffers(contactId)
createOffer(contactId, data)
updateOffer(contactId, offerId, data)
deleteOffer(contactId, offerId)

// Reports
reportContact(contactId, reason, details)

// Provider Dashboard
getProviderDashboard()

// Admin
getFlaggedProviders()
resolveReport(reportId, action)
getAnalytics(zone, dateFrom, dateTo)
exportAnalytics(format, zone, dateFrom, dateTo)

// Utilities
getUtilities()
createUtility(data)
updateUtility(id, data)
deleteUtility(id)
```

### js/geo.js (nuevo)
```javascript
// Geolocalización del navegador
getUserLocation() → Promise<{lat, lon}>

// Cálculo distancia (para display, no para filtrar)
haversineDistance(lat1, lon1, lat2, lon2) → km

// Inicializar mapa Leaflet
initMap(containerId, centerLat, centerLon, zoom)
addMarker(map, lat, lon, popupContent)
clusterMarkers(map, markers)
```

---

## PWA Configuration

### frontend/manifest.json
```json
{
  "name": "AgendaZonal - Guía de la Zona",
  "short_name": "AgendaZonal",
  "description": "Directorio de servicios y comercios de tu barrio",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#2563eb",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

### frontend/sw.js
```
Cache name: agendazonal-v1
Strategy: Network first, cache fallback
Precache: /, /search, /js/api.js, /js/app.js, /js/geo.js
Runtime cache: API responses (stale-while-revalidate for /api/contacts/search)
```

### main.py (modificar)
- Servir manifest.json y sw.js como archivos estáticos
- Servir /icons/ directory
- Agregar ruta /profile, /dashboard, /admin/reviews, etc.

---

## Migración de Datos

### Script de migración (backend/migrate_v2.py)
```python
1. ALTER TABLE contacts ADD avg_rating DEFAULT 0
2. ALTER TABLE contacts ADD review_count DEFAULT 0
3. ALTER TABLE contacts ADD verification_level DEFAULT 0
4. ALTER TABLE contacts ADD status DEFAULT 'active'
5. UPDATE contacts SET verification_level = 1 WHERE is_verified = 1
6. CREATE TABLE reviews (...)
7. CREATE TABLE offers (...)
8. CREATE TABLE lead_events (...)
9. CREATE TABLE reports (...)
10. CREATE TABLE utility_items (...)
11. CREATE INDEX idx_contacts_geo ON contacts(latitude, longitude)
```

El campo `is_verified` se MANTIENE por compatibilidad hacia atrás. `verification_level` es el nuevo campo canónico.

---

## Testing Strategy

### Tests Unitarios Nuevos
- `test_geo.py`: Haversine accuracy, bounding box calculations
- `test_reviews.py`: rating validation, photo validation
- `test_offers.py`: expiry logic, discount validation
- `test_reports.py`: auto-flag logic (3 reports → flagged)

### Tests de Integración Nuevos
- `test_geo_search.py`: search con/sin geo, combinación con category
- `test_reviews_flow.py`: crear → pendiente → aprobar → rating actualiza
- `test_offers_flow.py`: crear → activa → expira → no visible
- `test_reports_flow.py`: reportar 3 veces → flagged → admin resuelve
- `test_provider_dashboard.py`: métricas correctas
- `test_whatsapp_leads.py`: click → registra → visible en dashboard

### Tests Existentes
- TODOS deben seguir pasando sin cambios
- Si algún test falla, es regresión → debe arreglarse

---

## Dependencias Nuevas (requirements.txt)

```txt
# Ya existentes (no cambiar)
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.36
bcrypt==4.2.1
pyjwt==2.10.1
python-multipart==0.0.17
pydantic[email]==2.10.0
Pillow==11.1.0
python-dotenv==1.0.1
slowapi==0.1.9
pydantic-settings==2.7.0

# Nuevas
alembic==1.14.0          # Migraciones de schema
```

NOTA: Alembic es opcional pero recomendado. Si no se quiere agregar complejidad, las migraciones se pueden hacer con scripts SQL directos (migrate_v2.py).
