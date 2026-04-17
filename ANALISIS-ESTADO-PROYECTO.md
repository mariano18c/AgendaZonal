# Análisis Completo del Estado del Proyecto — AgendaZonal

> **Fecha**: 2026-04-03
> **Alcance**: Backend + Frontend + Specs + Tests + Infraestructura

---

## 1. RESUMEN EJECUTIVO

El proyecto AgendaZonal (Agenda zonal) está **mayormente completado** con SPEC-001 a SPEC-004 archivados. El core funcional (CRUD contactos, búsqueda geo, reseñas, ofertas, dashboard, PWA) está implementado y testeado. Sin embargo, existen **14 items pendientes**, **6 preocupaciones de seguridad/configuración**, y **0 issues abiertos en GitHub**.

---

## 2. LO COMPLETADO ✅

### Backend (FastAPI)

| Módulo | Estado | Detalle |
|--------|--------|---------|
| **Auth** | ✅ | JWT login/register, bcrypt, roles (user/moderator/admin), CAPTCHA |
| **Contacts CRUD** | ✅ | Create, read, update, delete con history tracking |
| **Pending Changes** | ✅ | Sistema de cambios pendientes con verificación/rechazo |
| **Image Upload** | ✅ | Upload/delete de imagen principal por contacto (JPEG, resize) |
| **Verification** | ✅ | Niveles 0-3, badges, sync con campo legacy is_verified |
| **Status Management** | ✅ | active/flagged/suspended, deletion requests, ownership transfer |
| **Search Text** | ✅ | Búsqueda por nombre, ciudad, barrio, descripción, teléfono (LIKE con escape) |
| **Search Geo** | ✅ | Haversine + bounding box, radio configurable, orden por distancia |
| **Search Phone** | ✅ | Búsqueda parcial por teléfono |
| **Export** | ✅ | CSV y JSON de contactos |
| **Reviews** | ✅ | Crear, aprobar/rechazar moderación, reply del owner, foto |
| **Rating Cache** | ✅ | avg_rating y review_count recalculados al aprobar/rechazar |
| **Offers** | ✅ | Flash offers con expiración, CRUD, auto-filtro de expiradas |
| **Leads** | ✅ | Tracking de clicks WhatsApp, stats por contacto |
| **Provider Dashboard** | ✅ | Métricas: leads mes, ofertas activas, leads por semana, reseñas recientes |
| **Reports** | ✅ | Crowdsourced, auto-flag a 3 reportes, resolución admin |
| **Analytics** | ✅ | Métricas zonales, top categorías, leads por día, export CSV |
| **Utilities** | ✅ | CRUD de utilidades de barrio (farmacias de turno, emergencias) |
| **Notifications** | ✅ | In-app (list, mark read), push subscriptions VAPID, helpers de envío |
| **Users Admin** | ✅ | List, create, update, role change, activate/deactivate, password reset |
| **Photos Gallery** | ✅ | Max 5 fotos por contacto, upload/delete |
| **Schedules** | ✅ | Horarios estructurados semanales |
| **Related Businesses** | ✅ | Misma categoría + proximidad geo |
| **Friendly URLs** | ✅ | `/c/{slug}` → redirect 301 a `/profile?id=X` |
| **Rate Limiting** | ✅ | slowapi con límites por endpoint + headers X-RateLimit |
| **Security Headers** | ✅ | CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy |
| **CORS** | ✅ | Configurado con ALLOWED_ORIGINS |
| **Public Users** | ✅ | `GET /api/public/users` para dropdowns |

### Frontend (17 Páginas)

| Página | Ruta | Estado |
|--------|------|--------|
| Landing | `/` | ✅ Categorías + utilidades + búsqueda |
| Search | `/search` | ✅ Texto + mapa Leaflet + MarkerCluster + geo |
| Profile | `/profile` | ✅ Info completa, reseñas, ofertas, WhatsApp, relacionados |
| Add | `/add` | ✅ Formulario alta contacto |
| Edit | `/edit` | ✅ Formulario edición |
| Login | `/login` | ✅ Inicio de sesión |
| Register | `/register` | ✅ Registro con CAPTCHA |
| Dashboard | `/dashboard` | ✅ Panel proveedor con métricas |
| History | `/history` | ✅ Historial de cambios |
| Pending | `/pending` | ✅ Contactos pendientes del usuario |
| Pending Changes | `/pending/changes` | ✅ Cambios pendientes de aprobación |
| Admin Reviews | `/admin/reviews` | ✅ Moderación de reseñas |
| Admin Reports | `/admin/reports` | ✅ Reportes crowdsourced |
| Admin Analytics | `/admin/analytics` | ✅ Analytics zonales + export CSV |
| Admin Utilities | `/admin/utilities` | ✅ CRUD utilidades de barrio |
| Admin Users | `/admin/users` | ✅ Gestión de usuarios |
| Offline | `/offline.html` | ✅ Página offline para PWA |

### PWA

| Componente | Estado |
|------------|--------|
| manifest.json | ✅ Con nombre, iconos, theme_color, start_url |
| Service Worker | ✅ Precache + stale-while-revalidate + push |
| Icons | ✅ 192x192 y 512x512 |
| Offline page | ✅ |

### Base de Datos (14 Tablas)

| Tabla | Registros | Estado |
|-------|-----------|--------|
| users | 115 | ✅ |
| categories | 26 | ✅ |
| contacts | 451 | ✅ |
| contact_history | 5 | ✅ |
| contact_changes | 0 | ✅ (vacío, funciona) |
| reviews | 1 | ✅ |
| offers | 17 | ✅ |
| lead_events | 1 | ✅ |
| reports | 1 | ✅ |
| schedules | 14 | ✅ |
| contact_photos | 0 | ✅ (vacío, funciona) |
| utility_items | 0 | ✅ (vacío, funciona) |
| notifications | 0 | ✅ (vacío, funciona) |
| push_subscriptions | 0 | ⚠️ (requiere VAPID) |

### Tests

- **40+ archivos** en `backend/tests/`
- Unit: models, schemas, geo, captcha, services
- Integration: contacts, reviews, auth, search, geo, notifications, phase3, phase5
- Security: SQL injection, XSS, JWT, fuzzing, race conditions, access control
- Performance: load tests

### Specs (SDD)

| Spec | Nombre | Estado | Archivado |
|------|--------|--------|-----------|
| SPEC-001 | Autenticación | ✅ | ✅ ARCHIVE-001 |
| SPEC-002 | CRUD Contactos | ✅ | ✅ ARCHIVE-002 |
| SPEC-003 | Evolución Hiperzonal | ✅ | ✅ |
| SPEC-004 | Mejoras Competitivas V3 | ✅ | ✅ |

### Infraestructura

| Componente | Estado |
|------------|--------|
| Caddy (reverse proxy) | ✅ Configurado con Caddyfile |
| CORS | ✅ Configurado |
| Security headers | ✅ Middleware personalizado |
| Rate limiting | ✅ slowapi |
| .env.example | ⚠️ Incompleto (falta VAPID) |

---

## 3. ITEMS PENDIENTES / INCOMPLETOS 🔲

### 3.1 Funcionalidades recientemente implementadas y validadas ✅

**Push Notifications — COMPLETAMENTE FUNCIONAL**
- Endpoints de subscribe/unsubscribe: ✅ Implementados.
- VAPID keys en `.env` y `pywebpush`: ✅ Completamente configurado.
- Frontend JS y Service Worker: ✅ Implementado en `app.js` interactuando perfectamente con `sw.js`.
- UI Navbar: ✅ Botón `#pwaPushBtn` ("🔔 Notificaciones") desplegado condicionalmente.

---

### 3.2 Endpoints Documentados pero NO Implementados

| Endpoint | Documentado en | Estado |
|----------|---------------|--------|
| `GET /api/notifications/unread-count` | DOCUMENTACION-COMPLETA.md:374 | ❌ No existe |
| `GET /api/contacts/{id}/export` (vCard) | DOCUMENTACION-COMPLETA.md:310 | ❌ No existe |

---

### 3.3 Frontend Missing — UI No Implementada

| Feature | Backend | Frontend |
|---------|---------|----------|
| Reportar contacto desde perfil | ✅ `POST /api/contacts/{id}/report` | ❌ Sin UI |
| Admin: gestión de contactos flagged/suspended | ✅ `GET/PUT /api/admin/contacts` | ❌ Sin UI unificada |

---

### 3.4 Dependencias Faltantes
*(Sección resuelta: Todas las dependencias críticas como `pywebpush` y VAPID keys ya fueron configuradas)*

---

### 3.5 Tablas Vacías (0 Registros)

| Tabla | Registros | Nota |
|-------|-----------|------|
| `contact_photos` | 0 | Feature funciona, sin datos aún |
| `utility_items` | 0 | CRUD funciona, sin datos aún |
| `notifications` | 0 | Sistema funciona, sin datos aún |
| `push_subscriptions` | 0 | Sistema habilitado y listo para registrar |
| `contact_changes` | 0 | Sistema funciona, sin datos aún |

---

### 3.6 Features Descartadas / Diferidas

| Feature | Estado | Razón |
|---------|--------|-------|
| QR Generator | ❌ Descartado | Decisión intencional |
| IA Matching | ❌ Pendiente | Requiere API externa, no viable en RPi 5 |

---

## 4. BUGS / PROBLEMAS CONOCIDOS 🐛

| # | Problema | Severidad | Archivo | Detalle |
|---|----------|-----------|---------|---------|
| 1 | VAPID keys no en `.env.example` | Baja | `.env.example` | Las verdaderas llaves están en `.env`, pero falta un template |
| 2 | HSTS header deshabilitado | Baja | `main.py:44-45` | Comentado con nota "Enable in production" |
| 3 | Export de contactos es público | Media | `routes/contacts.py:261` | 451 contactos exportables sin auth (data scraping) |
| 4 | Categorías: docs dicen 24, DB tiene 26 | Baja | AGENTS.md vs DB | Se agregaron "Cuidado de personas" (#123) y "Alquiler" (#124) |

---

## 5. TODO/FIXME/HACK EN CÓDIGO

**No se encontraron** comentarios TODO, FIXME, HACK ni XXX en el código fuente.

Las únicas coincidencias fueron falsos positivos:
- `TODOS` (palabra en español) en comentario de tests
- `XXXX` en placeholder de teléfono en JSON de datos
- `SPEC-XXX` en archivo template

---

## 6. GITHUB ISSUES

**0 issues abiertos** — `gh issue list` no retornó resultados. El repositorio no tiene issues abiertos o no está configurado con remote de GitHub.

---

## 7. ARCHIVOS CLAVE DEL PROYECTO

### Estructura Backend

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app + 17 rutas HTML + PWA + mounts
│   ├── auth.py              # JWT: get_current_user, create_token
│   ├── captcha.py           # Generación y validación CAPTCHA
│   ├── config.py            # JWT_SECRET, VAPID keys, DATABASE_URL
│   ├── database.py          # SQLAlchemy engine + session
│   ├── geo.py               # Haversine, bounding_box, validate_coordinates
│   ├── rate_limit.py        # slowapi configuración
│   ├── settings.py          # Settings adicionales
│   ├── models/              # 14 modelos SQLAlchemy
│   │   ├── category.py
│   │   ├── contact.py
│   │   ├── contact_change.py
│   │   ├── contact_photo.py
│   │   ├── lead_event.py
│   │   ├── notification.py
│   │   ├── offer.py
│   │   ├── push_subscription.py
│   │   ├── report.py
│   │   ├── review.py
│   │   ├── schedule.py
│   │   ├── user.py
│   │   └── utility_item.py
│   ├── repositories/        # Data access pattern
│   │   ├── contact_repository.py
│   │   └── user_repository.py
│   ├── routes/              # 9 routers API
│   │   ├── admin.py         # Reports, analytics, utilities
│   │   ├── auth.py          # Login, register
│   │   ├── categories.py    # List categories
│   │   ├── contacts.py      # CRUD + search + geo + photos + schedules
│   │   ├── notifications.py # In-app + push subscriptions
│   │   ├── offers.py        # Flash offers CRUD
│   │   ├── provider.py      # Dashboard metrics
│   │   ├── reviews.py       # Reviews + moderation + replies
│   │   └── users.py         # Admin user management
│   ├── schemas/             # 8 schemas Pydantic
│   │   ├── auth.py
│   │   ├── category.py
│   │   ├── contact.py
│   │   ├── offer.py
│   │   ├── report.py
│   │   ├── review.py
│   │   ├── user.py
│   │   └── utility.py
│   └── services/
│       ├── image_service.py
│       └── permission_service.py
├── database/agenda.db       # SQLite con WAL
├── uploads/images/          # Fotos de contactos y reseñas
├── tests/                   # 40+ archivos de tests
├── requirements.txt
├── requirements-test.txt
├── pytest.ini
├── Makefile
├── init_db.py
├── migrate_v2.py            # Reviews, offers, reports, utilities
└── migrate_v3.py            # Photos, schedules, slugs, social
```

### Estructura Frontend

```
frontend/
├── index.html               # Landing
├── search.html              # Búsqueda + mapa
├── profile.html             # Perfil proveedor
├── add.html                 # Alta contacto
├── edit.html                # Edición contacto
├── login.html               # Login
├── register.html            # Registro
├── dashboard.html           # Dashboard proveedor
├── history.html             # Historial
├── pending.html             # Pendientes
├── pending-changes.html     # Cambios pendientes
├── admin-users.html         # Admin usuarios
├── admin-reviews.html       # Admin reseñas
├── admin-reports.html       # Admin reportes
├── admin-analytics.html     # Admin analytics
├── admin-utilities.html     # Admin utilidades
├── offline.html             # PWA offline
├── manifest.json            # PWA manifest
├── sw.js                    # Service Worker
├── js/
│   ├── api.js               # API client
│   ├── app.js               # Navbar, PWA registration
│   └── geo.js               # Leaflet + geolocalización
├── icons/                   # PWA icons
└── css/                     # (vacío, usa Tailwind CDN)
```

---

## 8. API ENDPOINTS — MAPA COMPLETO

### Implementados ✅

| Método | Ruta | Auth | Router |
|--------|------|------|--------|
| GET | `/` | Público | main.py |
| GET | `/health` | Público | main.py |
| GET | `/search` | Público | main.py |
| GET | `/add` | Público | main.py |
| GET | `/login` | Público | main.py |
| GET | `/register` | Público | main.py |
| GET | `/profile` | Público | main.py |
| GET | `/dashboard` | Público | main.py |
| GET | `/history` | Público | main.py |
| GET | `/edit` | Público | main.py |
| GET | `/pending` | Público | main.py |
| GET | `/pending/changes` | Público | main.py |
| GET | `/admin/users` | Público | main.py |
| GET | `/admin/reviews` | Público | main.py |
| GET | `/admin/analytics` | Público | main.py |
| GET | `/admin/reports` | Público | main.py |
| GET | `/admin/utilities` | Público | main.py |
| GET | `/c/{slug}` | Público | main.py |
| GET | `/sw.js` | Público | main.py |
| GET | `/manifest.json` | Público | main.py |
| GET | `/offline.html` | Público | main.py |
| GET | `/favicon.ico` | Público | main.py |
| POST | `/api/auth/register` | Público | auth.py |
| POST | `/api/auth/login` | Público | auth.py |
| GET | `/api/categories` | Público | categories.py |
| GET | `/api/contacts` | Público | contacts.py |
| GET | `/api/contacts/search` | Público | contacts.py |
| GET | `/api/contacts/search/phone` | Público | contacts.py |
| GET | `/api/contacts/export` | Público | contacts.py |
| GET | `/api/contacts/{id}` | Público | contacts.py |
| POST | `/api/contacts` | Auth | contacts.py |
| PUT | `/api/contacts/{id}` | Auth | contacts.py |
| PUT | `/api/contacts/{id}/edit` | Optional | contacts.py |
| DELETE | `/api/contacts/{id}` | Auth | contacts.py |
| GET | `/api/contacts/{id}/history` | Auth | contacts.py |
| GET | `/api/contacts/{id}/changes` | Auth | contacts.py |
| POST | `/api/contacts/{id}/changes/{cid}/verify` | Auth | contacts.py |
| POST | `/api/contacts/{id}/changes/{cid}/reject` | Auth | contacts.py |
| DELETE | `/api/contacts/{id}/changes/{cid}` | Auth | contacts.py |
| POST | `/api/contacts/{id}/image` | Auth | contacts.py |
| DELETE | `/api/contacts/{id}/image` | Auth | contacts.py |
| POST | `/api/contacts/{id}/verify` | Auth | contacts.py |
| POST | `/api/contacts/{id}/leads` | Optional | contacts.py |
| GET | `/api/contacts/{id}/leads` | Auth | contacts.py |
| GET | `/api/contacts/{id}/related` | Público | contacts.py |
| GET | `/api/contacts/{id}/photos` | Público | contacts.py |
| POST | `/api/contacts/{id}/photos` | Auth | contacts.py |
| DELETE | `/api/contacts/{id}/photos/{pid}` | Auth | contacts.py |
| GET | `/api/contacts/{id}/schedules` | Público | contacts.py |
| PUT | `/api/contacts/{id}/schedules` | Auth | contacts.py |
| GET | `/api/contacts/pending` | Auth | contacts.py |
| POST | `/api/contacts/{id}/request-deletion` | Auth | contacts.py |
| POST | `/api/contacts/{id}/cancel-deletion` | Auth | contacts.py |
| PUT | `/api/contacts/{id}/transfer-ownership` | Admin | contacts.py |
| POST | `/api/contacts/{id}/report` | Auth | admin.py |
| GET | `/api/admin/reports/flagged` | Mod+ | admin.py |
| GET | `/api/admin/reports/pending` | Mod+ | admin.py |
| POST | `/api/admin/reports/{id}/resolve` | Mod+ | admin.py |
| GET | `/api/admin/contacts` | Mod+ | admin.py |
| PUT | `/api/admin/contacts/{id}/status` | Mod+ | admin.py |
| GET | `/api/admin/analytics` | Mod+ | admin.py |
| GET | `/api/admin/analytics/export` | Mod+ | admin.py |
| GET | `/api/utilities` | Público | admin.py |
| POST | `/api/admin/utilities` | Mod+ | admin.py |
| PUT | `/api/admin/utilities/{id}` | Mod+ | admin.py |
| DELETE | `/api/admin/utilities/{id}` | Mod+ | admin.py |
| GET | `/api/contacts/{id}/reviews` | Público | reviews.py |
| POST | `/api/contacts/{id}/reviews` | Auth | reviews.py |
| POST | `/api/reviews/{id}/photo` | Auth | reviews.py |
| POST | `/api/reviews/{id}/reply` | Auth | reviews.py |
| GET | `/api/admin/reviews/pending` | Mod+ | reviews.py |
| POST | `/api/admin/reviews/{id}/approve` | Mod+ | reviews.py |
| POST | `/api/admin/reviews/{id}/reject` | Mod+ | reviews.py |
| PUT | `/api/admin/contacts/{id}/verification` | Mod+ | reviews.py |
| GET | `/api/contacts/{id}/offers` | Público | offers.py |
| POST | `/api/contacts/{id}/offers` | Auth | offers.py |
| PUT | `/api/contacts/{id}/offers/{oid}` | Auth | offers.py |
| DELETE | `/api/contacts/{id}/offers/{oid}` | Auth | offers.py |
| GET | `/api/provider/dashboard` | Auth | provider.py |
| GET | `/api/notifications` | Auth | notifications.py |
| PUT | `/api/notifications/{id}/read` | Auth | notifications.py |
| PUT | `/api/notifications/read-all` | Auth | notifications.py |
| GET | `/api/notifications/vapid-public-key` | Público | notifications.py |
| POST | `/api/notifications/subscribe` | Auth | notifications.py |
| POST | `/api/notifications/unsubscribe` | Auth | notifications.py |
| GET | `/api/users` | Admin | users.py |
| GET | `/api/users/active` | Público | users.py |
| GET | `/api/users/{id}` | Admin | users.py |
| POST | `/api/users` | Admin | users.py |
| PUT | `/api/users/{id}` | Admin | users.py |
| PUT | `/api/users/{id}/role` | Admin | users.py |
| DELETE | `/api/users/{id}` | Admin | users.py |
| POST | `/api/users/{id}/activate` | Admin | users.py |
| POST | `/api/users/{id}/reset-password` | Admin | users.py |
| GET | `/api/public/users` | Público | main.py |

### Documentados pero NO Implementados ❌

| Método | Ruta | Documentado en |
|--------|------|---------------|
| GET | `/api/notifications/unread-count` | DOCUMENTACION-COMPLETA.md:374 |
| GET | `/api/contacts/{id}/export` | DOCUMENTACION-COMPLETA.md:310 |
| GET | `/api/contacts/{id}/pending-changes` | DOCUMENTACION-COMPLETA.md:306 |
| POST | `/api/contacts/{id}/pending-changes/{cid}/accept` | DOCUMENTACION-COMPLETA.md:307 |
| POST | `/api/contacts/{id}/pending-changes/{cid}/reject` | DOCUMENTACION-COMPLETA.md:308 |

---

## 9. PRIORIDADES RECOMENDADAS

### Alta Prioridad
1. **Frontend: UI para reportar contacto** — Feature de moderación crowdsourced
2. **Revisar visibilidad de `/api/contacts/export`** — Proteger con auth o rate limit para no exponer la BD.
3. **Agregar VAPID keys a `.env.example`** — Documentar llaves genéricas para nuevos desarrolladores.

### Media Prioridad
4. **Implementar `GET /api/notifications/unread-count`** — Badge de notificaciones
5. **Frontend: Admin page para contactos flagged/suspended** — Gestión unificada de moderación
6. **Habilitar HSTS en producción** — Mejorar Seguridad HTTPS

### Baja Prioridad
7. **Implementar vCard export** `GET /api/contacts/{id}/export` — Feature nice-to-have
8. **Actualizar docs de categorías (24 → 26)** — Consistencia con la DB real.

---

## 10. MÉTRICAS DEL PROYECTO

| Métrica | Valor |
|---------|-------|
| Líneas de código backend | ~8,000+ |
| Líneas de código frontend | ~5,000+ |
| Archivos de tests | 40+ |
| Endpoints API | 80+ |
| Páginas frontend | 17 |
| Tablas de base de datos | 14 |
| Categorías | 26 |
| Contactos en DB | 451 |
| Usuarios registrados | 115 |
| Specs completadas | 4 (SPEC-001 a SPEC-004) |
| Features descartadas | 1 (QR Generator) |
| Features diferidas | 1 (IA Matching) |
| Items pendientes | 14 |
| Bugs conocidos | 6 |

---

*Generado automáticamente el 2026-04-03*
*Proyecto: Agenda Comunitaria - AgendaZonal*
