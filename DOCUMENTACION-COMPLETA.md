# AgendaZonal — Documentación Técnica Completa

> Generado: 2026-03-29
> Stack: FastAPI + SQLite + HTML/Tailwind CSS/Vanilla JS
> Plataforma: Raspberry Pi 5 (4GB RAM)
> Estado: Producción

---

## 1. Visión General

AgendaZonal es un directorio hiperlocal de servicios y comercios para barrios de Rosario/Ibarlucea, Argentina. Reemplaza revistas publicitarias físicas con una plataforma web PWA con búsqueda geo, reseñas, WhatsApp integration, y ofertas flash.

**Stack:**
- **Backend**: Python 3.12, FastAPI, SQLAlchemy, SQLite
- **Frontend**: HTML5, Tailwind CSS (CDN), Vanilla JS
- **Mapas**: Leaflet.js + OpenStreetMap
- **Autenticación**: JWT (pyjwt)
- **Rate Limiting**: slowapi
- **Imágenes**: Pillow (resize JPEG)
- **Geo**: Haversine formula (Python puro, sin PostGIS)

---

## 2. Estructura del Proyecto

```
AgendaZonal/
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── routes/          # FastAPI routers
│   │   ├── schemas/         # Pydantic schemas (validación)
│   │   ├── auth.py          # JWT creation/verification
│   │   ├── config.py        # Settings (JWT_SECRET, etc.)
│   │   ├── database.py      # SQLite engine + session
│   │   ├── geo.py           # Haversine + bounding box
│   │   ├── rate_limit.py    # slowapi config
│   │   └── main.py          # FastAPI app + routes
│   ├── database/
│   │   └── agenda.db        # SQLite database file
│   ├── uploads/
│   │   └── images/          # Uploaded photos
│   ├── tests/
│   │   ├── conftest.py      # Fixtures (in-memory DB, auth, factories)
│   │   ├── integration/     # API integration tests
│   │   ├── unit/            # Unit tests
│   │   ├── security/        # XSS/SQLi tests
│   │   └── performance/     # Load tests
│   ├── init_db.py           # Create tables + seed categories
│   ├── migrate_v2.py        # V2 migration (geo, reviews, offers, reports)
│   ├── migrate_v3.py        # V3 migration (photos, schedules, social, slugs)
│   └── requirements.txt
├── frontend/
│   ├── index.html           # Landing page
│   ├── search.html          # Search + map + geo
│   ├── profile.html         # Contact profile
│   ├── add.html             # Add contact form
│   ├── edit.html            # Edit contact form
│   ├── login.html           # Login
│   ├── register.html        # Register
│   ├── dashboard.html       # Provider dashboard
│   ├── history.html         # Contact history
│   ├── pending.html         # Pending contacts
│   ├── pending-changes.html # Pending changes (mod)
│   ├── admin-users.html     # User management (admin)
│   ├── admin-reviews.html   # Review moderation (mod+)
│   ├── admin-reports.html   # Report resolution (mod+)
│   ├── admin-analytics.html # Analytics + CSV export (mod+)
│   ├── admin-utilities.html # Barrio utilities CRUD (mod+)
│   ├── offline.html         # PWA offline page
│   ├── sw.js                # Service Worker
│   ├── manifest.json        # PWA manifest
│   ├── icons/               # PWA icons (192, 512)
│   ├── js/
│   │   ├── api.js           # API client functions
│   │   ├── app.js           # Navbar, PWA registration
│   │   └── geo.js           # Leaflet map + geolocation utils
│   └── css/                 # (empty, uses Tailwind CDN)
└── SPECS/                   # SDD documentation
    ├── PROPOSAL-001/002/003/
    ├── SPEC-001/002/003/004/
    ├── DESIGN-001/002/003/
    └── ARCHIVE/
```

---

## 3. Base de Datos — Schema Completo

### 3.1 users
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | Autoincrement |
| username | VARCHAR(50) UNIQUE | Nombre de usuario |
| email | VARCHAR(255) UNIQUE | Email |
| phone_area_code | VARCHAR(5) | Código de área (ej: 0341) |
| phone_number | VARCHAR(20) | Número de teléfono |
| password_hash | VARCHAR(255) | bcrypt hash |
| role | VARCHAR(20) | user / moderator / admin |
| is_active | BOOLEAN | Cuenta activa |
| deactivated_at | DATETIME | Fecha de desactivación |
| deactivated_by | INTEGER FK | Admin que desactivó |
| created_at | DATETIME | Fecha de creación |

### 3.2 categories
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | Autoincrement |
| code | INTEGER UNIQUE | Código de categoría (100-123, 999) |
| name | VARCHAR(100) | Nombre visible |
| icon | VARCHAR(50) | Emoji o icono |
| description | VARCHAR(255) | Descripción |

**Categorías predefinidas (24):**
100=Plomero/a, 101=Gasista, 102=Electricista, 103=Peluquería/Barbería, 104=Albañil, 105=Pintor, 106=Carpintero/a, 107=Supermercado, 108=Carnicería, 109=Verdulería, 110=Panadería, 111=Tienda de ropa, 112=Farmacia, 113=Librería, 114=Bar, 115=Restaurant, 116=Club, 117=Bazar, 118=Veterinaria, 119=Ferretería, 120=Kiosco, 121=Juguetería, 122=Polirrubro, 123=Servicios Profesionales, 999=Otro

### 3.3 contacts
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| name | VARCHAR(100) | Nombre del negocio |
| phone | VARCHAR(20) | Teléfono |
| email | VARCHAR(255) | Email |
| address | VARCHAR(255) | Dirección |
| city | VARCHAR(100) | Ciudad |
| neighborhood | VARCHAR(100) | Barrio |
| category_id | INTEGER FK | → categories.id |
| description | VARCHAR(500) | Descripción corta |
| user_id | INTEGER FK | → users.id (creador) |
| schedule | VARCHAR(200) | Horario en texto (legacy) |
| website | VARCHAR(255) | Sitio web |
| photo_path | VARCHAR(500) | Foto principal |
| latitude | FLOAT | Latitud GPS |
| longitude | FLOAT | Longitud GPS |
| maps_url | VARCHAR(500) | Google Maps URL |
| is_verified | BOOLEAN | Legacy: verificado |
| verified_by | INTEGER FK | Usuario que verificó |
| verified_at | DATETIME | Fecha verificación |
| verification_level | INTEGER | 0=sin_verificar, 1=básico, 2=documentado, 3=premium |
| status | VARCHAR(20) | active / flagged / suspended |
| avg_rating | FLOAT | Rating promedio (cacheado) |
| review_count | INTEGER | Cantidad reseñas (cacheado) |
| pending_changes_count | INTEGER | Cambios pendientes |
| instagram | VARCHAR(100) | @usuario o URL Instagram |
| facebook | VARCHAR(255) | URL Facebook |
| about | TEXT | Descripción larga (2000 chars) |
| slug | VARCHAR(200) | URL amigable (ej: juan-perez-plomero-1) |
| created_at | DATETIME | |
| updated_at | DATETIME | |

**Índices:** geo (lat,lon), status, verification_level, avg_rating, slug

### 3.4 contact_history
| Campo | Tipo |
|-------|------|
| id | INTEGER PK |
| contact_id | INTEGER FK |
| user_id | INTEGER FK |
| field_name | VARCHAR |
| old_value | VARCHAR |
| new_value | VARCHAR |
| changed_at | DATETIME |

### 3.5 contact_changes (pending edits)
| Campo | Tipo |
|-------|------|
| id | INTEGER PK |
| contact_id | INTEGER FK |
| user_id | INTEGER FK |
| field_name | VARCHAR |
| old_value | VARCHAR |
| new_value | VARCHAR |
| is_verified | BOOLEAN |
| verified_by | INTEGER FK |
| verified_at | DATETIME |
| created_at | DATETIME |

### 3.6 reviews
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| contact_id | INTEGER FK | |
| user_id | INTEGER FK | |
| rating | INTEGER | 1-5 |
| comment | TEXT | Max 500 chars |
| photo_path | VARCHAR(500) | Foto de reseña |
| is_approved | BOOLEAN | Moderación |
| approved_by | INTEGER FK | Mod que aprobó |
| approved_at | DATETIME | |
| created_at | DATETIME | |

**Constraint:** UNIQUE(contact_id, user_id) — un usuario, una reseña por contacto

### 3.7 offers
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| contact_id | INTEGER FK | |
| title | VARCHAR(200) | Título oferta |
| description | VARCHAR(500) | Descripción |
| discount_pct | INTEGER | 1-99, nullable |
| expires_at | DATETIME | Fecha expiración |
| is_active | BOOLEAN | |
| created_at | DATETIME | |

### 3.8 lead_events
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| contact_id | INTEGER FK | |
| user_id | INTEGER FK | NULL si anónimo |
| source | VARCHAR(20) | whatsapp |
| created_at | DATETIME | |

### 3.9 reports
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| contact_id | INTEGER FK | |
| user_id | INTEGER FK | |
| reason | VARCHAR(20) | spam / falso / inapropiado / cerrado |
| details | TEXT | |
| is_resolved | BOOLEAN | |
| resolved_by | INTEGER FK | |
| resolved_at | DATETIME | |
| created_at | DATETIME | |

**Constraint:** UNIQUE(contact_id, user_id)
**Auto-flag:** 3 reportes distintos → contact.status='flagged'

### 3.10 utility_items
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| type | VARCHAR(20) | farmacia_turno / emergencia / otro |
| name | VARCHAR(200) | |
| address | VARCHAR(255) | |
| phone | VARCHAR(20) | |
| schedule | VARCHAR(200) | |
| lat / lon | FLOAT | |
| city | VARCHAR(100) | |
| is_active | BOOLEAN | |
| created_by | INTEGER FK | |
| created_at / updated_at | DATETIME | |

### 3.11 notifications
| Campo | Tipo |
|-------|------|
| id | INTEGER PK |
| user_id | INTEGER FK |
| type | VARCHAR(50) |
| message | VARCHAR(500) |
| contact_id | INTEGER FK |
| is_read | BOOLEAN |
| created_at | DATETIME |

### 3.12 contact_photos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| contact_id | INTEGER FK | |
| photo_path | VARCHAR(500) | |
| caption | VARCHAR(200) | |
| sort_order | INTEGER | Orden de visualización |

**Max 5 fotos por contacto**

### 3.13 schedules
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| contact_id | INTEGER FK | |
| day_of_week | INTEGER | 0=Lunes ... 6=Domingo |
| open_time | VARCHAR(5) | "08:00" o NULL (cerrado) |
| close_time | VARCHAR(5) | "18:00" |

---

## 4. API Endpoints

### 4.1 Auth
| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/api/auth/register` | Público | Registrar usuario (rate: 3/min) |
| POST | `/api/auth/login` | Público | Login, retorna JWT (rate: 5/min) |
| GET | `/api/auth/me` | User | Info usuario actual |
| POST | `/api/auth/bootstrap-admin` | Público | Crear primer admin (solo DB vacía) |

### 4.2 Categories
| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/api/categories` | Público | Listar categorías |

### 4.3 Contacts
| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/api/contacts` | Público | Listar contactos |
| POST | `/api/contacts` | User | Crear contacto (rate: 10/min) |
| GET | `/api/contacts/search` | Público | Buscar (texto + geo + category) (rate: 30/min) |
| GET | `/api/contacts/search/phone` | Público | Buscar por teléfono |
| GET | `/api/contacts/{id}` | Público | Detalle contacto |
| PUT | `/api/contacts/{id}` | Owner | Editar contacto |
| DELETE | `/api/contacts/{id}` | Owner/Admin | Eliminar contacto |
| GET | `/api/contacts/{id}/history` | Owner | Historial de cambios |
| GET | `/api/contacts/{id}/pending-changes` | Owner | Cambios pendientes |
| POST | `/api/contacts/{id}/pending-changes/{cid}/accept` | Owner | Aceptar cambio |
| POST | `/api/contacts/{id}/pending-changes/{cid}/reject` | Owner | Rechazar cambio |
| POST | `/api/contacts/{id}/verify` | User | Verificar contacto |
| GET | `/api/contacts/{id}/export` | Público | Exportar vCard |
| GET | `/api/contacts/export` | Público | Exportar CSV |
| POST | `/api/contacts/{id}/upload-image` | Owner | Subir foto principal |
| POST | `/api/contacts/{id}/leads` | Opcional | Registrar click WhatsApp |
| GET | `/api/contacts/{id}/leads` | Owner | Ver leads |
| GET | `/api/contacts/{id}/photos` | Público | Galería de fotos |
| POST | `/api/contacts/{id}/photos` | Owner | Subir foto (max 5) |
| DELETE | `/api/contacts/{id}/photos/{pid}` | Owner | Eliminar foto |
| GET | `/api/contacts/{id}/schedules` | Público | Horarios estructurados |
| PUT | `/api/contacts/{id}/schedules` | Owner | Actualizar horarios |
| GET | `/api/contacts/{id}/related` | Público | Negocios relacionados |

### 4.4 Reviews
| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/api/contacts/{id}/reviews` | User | Crear reseña (rate: 5/hora) |
| GET | `/api/contacts/{id}/reviews` | Público | Listar reseñas aprobadas |
| POST | `/api/reviews/{id}/photo` | Autor | Subir foto a reseña |
| GET | `/api/admin/reviews/pending` | Mod+ | Reseñas pendientes |
| POST | `/api/admin/reviews/{id}/approve` | Mod+ | Aprobar reseña |
| POST | `/api/admin/reviews/{id}/reject` | Mod+ | Rechazar reseña |
| PUT | `/api/admin/contacts/{id}/verification` | Mod+ | Cambiar nivel verificación |

### 4.5 Offers
| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/api/contacts/{id}/offers` | Owner | Crear oferta |
| GET | `/api/contacts/{id}/offers` | Público | Listar ofertas activas |
| PUT | `/api/contacts/{id}/offers/{oid}` | Owner | Editar oferta |
| DELETE | `/api/contacts/{id}/offers/{oid}` | Owner | Eliminar oferta |

### 4.6 Provider Dashboard
| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/api/provider/dashboard` | User | Métricas del proveedor |

### 4.7 Admin
| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/api/contacts/{id}/report` | User | Reportar contacto |
| GET | `/api/admin/reports/flagged` | Mod+ | Proveedores flagged |
| POST | `/api/admin/reports/{id}/resolve` | Mod+ | Resolver reporte |
| GET | `/api/admin/analytics` | Mod+ | Métricas por zona |
| GET | `/api/admin/analytics/export` | Mod+ | Exportar CSV |
| GET | `/api/utilities` | Público | Listar utilidades |
| POST | `/api/admin/utilities` | Mod+ | Crear utilidad |
| PUT | `/api/admin/utilities/{id}` | Mod+ | Editar utilidad |
| DELETE | `/api/admin/utilities/{id}` | Mod+ | Soft-delete utilidad |

### 4.8 Users (admin)
| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/api/users` | Admin | Listar usuarios |
| PUT | `/api/users/{id}/role` | Admin | Cambiar rol |
| DELETE | `/api/users/{id}` | Admin | Desactivar usuario |
| POST | `/api/users/{id}/activate` | Admin | Reactivar usuario |
| GET | `/api/users/stats` | Admin | Estadísticas usuarios |

### 4.9 Notifications
| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/api/notifications` | User | Listar notificaciones |
| PUT | `/api/notifications/{id}/read` | User | Marcar como leída |
| PUT | `/api/notifications/read-all` | User | Marcar todas leídas |
| GET | `/api/notifications/unread-count` | User | Contador no leídas |

### 4.10 Health
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado del sistema (DB + disco) |

### 4.11 PWA
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/sw.js` | Service Worker |
| GET | `/manifest.json` | PWA Manifest |
| GET | `/offline.html` | Página offline |
| GET | `/c/{slug}` | URL amigable → redirect 301 |

---

## 5. Páginas Frontend

| URL | Archivo | Función |
|-----|---------|---------|
| `/` | index.html | Landing: categorías, búsqueda |
| `/search` | search.html | Búsqueda: texto, geo, mapa Leaflet, radio |
| `/profile?id=X` | profile.html | Perfil: info, fotos, reseñas, ofertas, WhatsApp, relacionados |
| `/c/{slug}` | redirect | URL amigable → /profile?id=X |
| `/add` | add.html | Formulario agregar contacto |
| `/edit?id=X` | edit.html | Formulario editar contacto |
| `/login` | login.html | Login |
| `/register` | register.html | Registro |
| `/dashboard` | dashboard.html | Dashboard proveedor: métricas, gráfico leads |
| `/history?id=X` | history.html | Historial de cambios de un contacto |
| `/pending` | pending.html | Contactos pendientes del usuario |
| `/pending/changes` | pending-changes.html | Cambios pendientes (owner) |
| `/admin/users` | admin-users.html | Gestión usuarios (admin) |
| `/admin/reviews` | admin-reviews.html | Moderación reseñas (mod+) |
| `/admin/reports` | admin-reports.html | Resolución reportes (mod+) |
| `/admin/analytics` | admin-analytics.html | Analytics + CSV export (mod+) |
| `/admin/utilities` | admin-utilities.html | CRUD utilidades barrio (mod+) |

---

## 6. Autenticación y Autorización

### JWT Flow
1. Usuario se registra o hace login
2. Backend crea JWT con `{user_id, iat}` firmado con `JWT_SECRET`
3. Frontend guarda token en `localStorage`
4. Cada request autenticado incluye `Authorization: Bearer <token>`
5. `get_current_user` decodifica JWT y carga usuario de DB

### Roles
- **user**: CRUD propio contactos, crear reseñas, reportar
- **moderator**: Todo lo de user + aprobar/rechazar reseñas, resolver reportes, analytics, utilidades
- **admin**: Todo lo de moderator + gestionar usuarios, bootstrap-admin

### Rate Limiting (slowapi)
| Endpoint | Límite |
|----------|--------|
| Register | 3/min por IP |
| Login | 5/min por IP |
| Search | 30/min por IP |
| Create contact | 10/min por IP |
| Create review | 5/hora por usuario |
| Global fallback | 60/min por IP |

Desactivado en tests (`TESTING=1` env var).

---

## 7. Geo / Mapas

### Haversine (backend/app/geo.py)
- `haversine_km(lat1, lon1, lat2, lon2)` → distancia en km
- `bounding_box(center_lat, center_lon, radius_km)` → BoundingBox para pre-filtro
- `validate_coordinates(lat, lon)` → validación de coordenadas

### Estrategia de Búsqueda Geo
1. Bounding box query (WHERE lat BETWEEN... AND lon BETWEEN...) — usa índices numéricos
2. Haversine refinamiento sobre el subset — precisión matemática
3. Ordenar por distancia ascendente
4. Incluir `distance_km` en cada resultado

### Mapas (frontend/js/geo.js)
- Leaflet.js desde CDN (mismo patrón que Tailwind)
- OpenStreetMap tiles gratuitos
- Marcadores por cada contacto con popups
- Círculo de radio de búsqueda
- Marcador de ubicación del usuario
- Fit bounds automático

---

## 8. PWA Configuration

### Service Worker (sw.js)
- **Estrategia HTML**: Network first, cache fallback, offline.html
- **Estrategia assets**: Stale-while-revalidate
- **Precache**: `/`, `/search`, `/offline.html`, `api.js`, `app.js`, `geo.js`
- **API**: No cache (network only)

### Manifest (manifest.json)
- name: "AgendaZonal - Guía de la Zona"
- start_url: "/"
- display: standalone
- theme_color: #2563eb
- icons: 192x192, 512x512

---

## 9. Tests

### Estructura
```
tests/
├── conftest.py           # Fixtures principales
├── integration/
│   ├── test_auth.py      # Login, registro, permisos
│   ├── test_search.py    # Búsqueda texto
│   ├── test_geo_search.py # Búsqueda geo
│   ├── test_reviews.py   # Reseñas + verificación
│   ├── test_phase3.py    # Ofertas + leads + dashboard
│   ├── test_phase5.py    # Reports + analytics + utilities
│   ├── test_contacts.py  # CRUD contactos
│   ├── test_categories.py
│   ├── test_users.py
│   ├── test_db_integrity.py # FK constraints
│   └── test_pending_changes.py
├── unit/
│   ├── test_models.py
│   ├── test_schemas.py
│   ├── test_geo.py       # Haversine + bounding box
│   └── test_utils.py
├── security/
│   ├── test_security.py  # XSS, SQLi, auth bypass
│   └── test_fuzzing.py   # Fuzzing payloads
└── performance/
    └── test_performance.py
```

### Fixtures Clave (conftest.py)
- `client`: TestClient de FastAPI
- `database_session`: In-memory SQLite con StaticPool
- `create_user`: Factory para crear usuarios
- `auth_headers(username, email)`: Registra usuario + retorna Bearer headers
- `contact_factory(headers, ...)`: Crea contacto via API
- `moderator_user`: Usuario con rol moderator
- `admin_headers`: Admin via bootstrap-admin (solo DB vacía)

### Ejecutar Tests
```bash
cd backend
python -m pytest tests/ -v --tb=short     # Todos
python -m pytest tests/ -x -q              # Rápido, stop en primer fallo
python -m pytest tests/unit/               # Solo unitarios
python -m pytest -m security               # Solo seguridad
```

**455 tests, 0 fallos.**

---

## 10. Migraciones

### migrate_v2.py
- Agrega a contacts: avg_rating, review_count, verification_level, status
- Crea tablas: reviews, offers, lead_events, reports, utility_items, notifications
- Crea índices: geo, status, verification, rating
- Migra is_verified → verification_level

### migrate_v3.py
- Agrega a contacts: instagram, facebook, about, slug
- Crea tablas: contact_photos, schedules
- Genera slugs para contactos existentes

**Ejecución:** `python migrate_v2.py` → `python migrate_v3.py`
**Idempotente:** Safe to run multiple times (verifica column/tabla existencia).

---

## 11. Configuración

### config.py
```python
JWT_SECRET = os.getenv("JWT_SECRET", "<default>")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
UPLOAD_MAX_SIZE = 10 * 1024 * 1024  # 10MB
RATE_LIMIT_DEFAULT = "100/hour"
```

### Environment Variables
- `JWT_SECRET`: Clave secreta JWT
- `ALLOWED_ORIGINS`: CORS origins (default: localhost:8000)
- `TESTING=1`: Desactiva rate limiting en tests

### database.py
```python
DATABASE_URL = "sqlite:///database/agenda.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
```

---

## 12. Cómo Ejecutar

```bash
cd backend
# (opcional) crear venv
python -m venv venv
source venv/bin/activate  # o venv\Scripts\activate en Windows

# instalar dependencias
pip install -r requirements.txt

# inicializar DB (primera vez)
python init_db.py

# migrar (si ya existe DB)
python migrate_v2.py
python migrate_v3.py

# iniciar servidor
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Abrir: **http://localhost:8000**

---

## 13. Dependencias (requirements.txt)

```
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
```

---

## 14. Decisiones de Arquitectura

| Decisión | Razón |
|----------|-------|
| SQLite + Haversine (no PostGIS) | RPi 5: 50MB RAM vs 600MB PostgreSQL, suficiente para <5k contactos |
| FastAPI + HTML (no Next.js) | Un solo stack Python, menos complejidad, menos RAM |
| Sin IA local (Ollama) | RPi 5 tiene 4GB RAM, no alcanza para LLM |
| WhatsApp deep links (no Business API) | Gratis, funcional, sin dependencia externa |
| Rating cacheado (no calculado) | Lectura frecuente, escritura infrecuente |
| Bounding box + Haversine | Rápido + preciso sin dependencia de extensiones geográficas |

---

## 15. Features Implementadas vs. Espec Original

| Feature | Estado |
|---------|--------|
| CRUD contactos | ✅ |
| Autenticación JWT | ✅ |
| Búsqueda texto + categoría | ✅ |
| Búsqueda geo por radio | ✅ |
| Mapa Leaflet interactivo | ✅ |
| Geolocalización GPS | ✅ |
| Sistema de reseñas (1-5) | ✅ |
| Moderación de reseñas | ✅ |
| Verificación por niveles (0-3) | ✅ |
| WhatsApp leads + tracking | ✅ |
| Ofertas flash con expiración | ✅ |
| Dashboard proveedor | ✅ |
| PWA (service worker + manifest) | ✅ |
| Rate limiting | ✅ |
| Reports crowdsourced | ✅ |
| Analytics zonales + CSV | ✅ |
| Utilidades barrio | ✅ |
| Galería de fotos (max 5) | ✅ |
| Horarios estructurados | ✅ |
| Redes sociales (IG, FB) | ✅ |
| Descripción larga | ✅ |
| Breadcrumbs | ✅ |
| Negocios relacionados | ✅ |
| Compartir (Web Share API) | ✅ |
| URLs amigables (/c/slug) | ✅ |
| Búsqueda por teléfono | ✅ |
| QR Generator | ❌ Descartado |
| IA Matching | ❌ Pendiente (API externa) |
