# Agent Configuration - Agenda de la zona (Gentle AI)

## Gentle AI Stack
- **Agent ID**: `antigravity`
- **Workflow**: Spec-Driven Development (SDD)
- **Status**: ✅ **GENTLE-READY** (CLI v1.18.2 Installed)
- **Config**: `.gga` (Guardian Angel) -> Migrated to `gentle-ai` binary ecosystem

## Proyecto
- **Nombre**: Agenda de la zona
- **Tipo**: Sistema web completo (FastAPI + SQLite + Tailwind CSS)
- **Stack**: FastAPI (Python), SQLite, HTML + Tailwind CSS + Vanilla JS
- **Plataforma**: Raspberry Pi 5 (4GB RAM)
- **Estado**: ✅ **COMPLETADO** (SPEC-001 a SPEC-004)

## SDD Workflow
Este proyecto sigue el flujo Spec-Driven Development.

### Fases SDD
1. **Explore** → ✅ Completado
2. **New** → ✅ Completado
3. **Spec** → ✅ Completado (SPEC-001, 002, 003, 004)
4. **Design** → ✅ Completado
5. **Tasks** → ✅ Completado
6. **Apply** → ✅ Completado (Backend + Frontend)
7. **Verify** → ✅ Completado
8. **Archive** → ✅ Completado (SPEC-001, 002, 003, 004)

### Comandos Disponibles
- `/sdd-explore` - Investigar el codebase
- `/sdd-new` - Crear propuesta de cambio
- `/sdd-apply` - Implementar tareas
- `/sdd-verify` - Verificar implementación
- `/sdd-archive` - Archivar especificaciones

## Estado del Proyecto

### Backend ✅ Completado
- FastAPI configurado con CORS
- SQLite configurado (24 categorías predefinidas)
- Autenticación JWT implementada
- CRUD completo de contactos
- Búsqueda por texto, categoría, teléfono y geolocalización
- Geo-búsqueda con Haversine + bounding box
- Sistema de reseñas con moderación y reply
- Ofertas flash con countdown
- Push notifications con VAPID
- Rate limiting con X-RateLimit headers
- Reportes crowdsourced + analytics + CSV export
- Utilidades de barrio
- CAPTCHA para registro
- Repositories + Services pattern
- Horarios estructurados + galería de fotos (max 5)

### Frontend ✅ Completado
- HTML + Tailwind CSS + Vanilla JS
- Responsive (celulares y computadoras)
- PWA instalable: manifest, Service Worker, icons, beforeinstallprompt
- Service Worker: precache, stale-while-revalidate, push notifications

### Páginas (17)
| Página | Ruta | Descripción |
|--------|------|-------------|
| Landing | `/` | Página principal con categorías y utilidades |
| Search | `/search` | Búsqueda por texto + mapa Leaflet con MarkerCluster |
| Profile | `/profile` | Perfil proveedor con carrusel, reseñas, WhatsApp, ofertas |
| Add | `/add` | Alta de contacto |
| Edit | `/edit` | Edición de contacto |
| Login | `/login` | Inicio de sesión |
| Register | `/register` | Registro con CAPTCHA |
| Dashboard | `/dashboard` | Panel proveedor (leads, rating, offers) |
| History | `/history` | Historial de cambios |
| Pending | `/pending` | Cambios pendientes de aprobación |
| Offline | `/offline.html` | Página offline para PWA |
| Admin Reviews | `/admin/reviews` | Moderación de reseñas |
| Admin Reports | `/admin/reports` | Reportes crowdsourced |
| Admin Analytics | `/admin/analytics` | Analytics zonales + export CSV |
| Admin Utilities | `/admin/utilities` | Utilidades de barrio (CRUD) |
| Admin Users | `/admin/users` | Gestión de usuarios |

### API Endpoints

| Método | Ruta | Acceso | Spec |
|--------|------|--------|------|
| GET | `/` | Público | 001 |
| GET | `/health` | Público | 001 |
| GET | `/search` | Público | 001 |
| GET | `/add` | Público | 001 |
| GET | `/login` | Público | 001 |
| GET | `/register` | Público | 001 |
| GET | `/profile` | Público | 003 |
| GET | `/dashboard` | Auth | 003 |
| GET | `/c/{slug}` | Público | 004 |
| POST | `/api/auth/register` | Público | 001 |
| POST | `/api/auth/login` | Público | 001 |
| GET | `/api/categories` | Público | 001 |
| GET | `/api/contacts` | Público | 002 |
| GET | `/api/contacts/search` | Público | 002+003 |
| GET | `/api/contacts/search/phone` | Público | 004 |
| GET | `/api/contacts/{id}` | Público | 002 |
| POST | `/api/contacts` | Auth | 002 |
| PUT | `/api/contacts/{id}` | Auth | 002 |
| DELETE | `/api/contacts/{id}` | Auth | 002 |
| GET | `/api/contacts/{id}/reviews` | Público | 003 |
| POST | `/api/contacts/{id}/reviews` | Auth | 003 |
| POST | `/api/contacts/{id}/leads` | Público | 003 |
| GET | `/api/contacts/{id}/related` | Público | 004 |
| GET | `/api/contacts/{id}/schedules` | Público | 004 |
| PUT | `/api/contacts/{id}/schedules` | Auth | 004 |
| POST | `/api/contacts/{id}/photos` | Auth | 004 |
| GET | `/api/contacts/{id}/photos` | Público | 004 |
| DELETE | `/api/contacts/{id}/photos/{photo_id}` | Auth | 004 |
| POST | `/api/reviews/{id}/reply` | Auth | 003 |
| PUT | `/api/admin/reviews/{id}/approve` | Mod | 003 |
| PUT | `/api/admin/reviews/{id}/reject` | Mod | 003 |
| PUT | `/api/admin/contacts/{id}/verification` | Mod | 003 |
| GET | `/api/admin/reviews/pending` | Mod | 003 |
| GET | `/api/admin/reports` | Mod | 003 |
| PUT | `/api/admin/reports/{id}/resolve` | Mod | 003 |
| GET | `/api/admin/analytics` | Mod | 003 |
| GET | `/api/admin/analytics/export` | Mod | 003 |
| CRUD | `/api/admin/utilities` | Mod | 003 |
| POST | `/api/notifications/subscribe` | Auth | 003 |
| GET | `/api/provider/dashboard` | Auth | 003 |
| GET | `/api/provider/contacts` | Auth | 003 |
| CRUD | `/api/provider/offers` | Auth | 003 |

### Base de Datos

| Tabla | Campos principales |
|-------|-------------------|
| users | id, username, email, phone_area_code, phone_number, password_hash, role, created_at |
| categories | id, code, name, icon, description |
| contacts | id, name, phone, email, address, city, neighborhood, category_id, description, about, instagram, facebook, schedule, latitude, longitude, slug, verification_level, status, user_id, created_at, updated_at |
| contact_photos | id, contact_id, filename, position, created_at |
| reviews | id, contact_id, user_id, rating, comment, status, reply_text, reply_at, reply_by, created_at |
| offers | id, contact_id, title, description, discount_pct, starts_at, expires_at, active, created_at |
| schedules | id, contact_id, day_of_week, open_time, close_time |
| lead_events | id, contact_id, channel, referrer, created_at |
| reports | id, contact_id, reporter_id, reason, status, resolved_by, resolved_at, created_at |
| notifications | id, user_id, title, body, url, read, created_at |
| push_subscriptions | id, user_id, endpoint, p256dh, auth, created_at |
| utility_items | id, name, category, phone, address, description, active, created_at |

### Categorías Predefinidas (24)
| Código | Nombre |
|--------|--------|
| 100 | Plomero/a |
| 101 | Gasista |
| 102 | Electricista |
| 103 | Peluquería/Barbería |
| 104 | Albañil |
| 105 | Pintor |
| 106 | Carpintero/a |
| 107 | Supermercado |
| 108 | Carnicería |
| 109 | Verdulería |
| 110 | Panadería |
| 111 | Tienda de ropa |
| 112 | Farmacia |
| 113 | Librería |
| 114 | Bar |
| 115 | Restaurant |
| 116 | Club |
| 117 | Bazar |
| 118 | Veterinaria |
| 119 | Ferretería |
| 120 | Kiosco |
| 121 | Juguetería |
| 122 | Polirrubro |
| 999 | Otro |

## Tests
- **40+ archivos** en `backend/tests/`
- Unit: models, schemas, geo, captcha, services
- Integration: contacts, reviews, auth, search, geo, notifications
- Security: SQL injection, JWT, fuzzing, race conditions, access control

## Cómo Ejecutar

```bash
cd backend
source venv/bin/activate  # o venv\Scripts\activate en Windows
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Luego abrir: **http://localhost:8000**

## Configuración Regional
- **Idioma**: Español (Español Rioplatense)
- **Zona horaria**: America/Argentina/Buenos_Aires

## Further Documentation

Para documentación detallada de configuración, convenciones y diseño, ver:

| Archivo | Descripción |
|---------|-------------|
| [`.agent/README.md`](.agent/README.md) | Guía de inicio, stack, commands frecuentes |
| [`.agent/CONVENTIONS.md`](.agent/CONVENTIONS.md) | Convenciones de código Python y JavaScript |
| [`.agent/DESIGN.md`](.agent/DESIGN.md) | Sistema de diseño, paleta de colores, componentes |
| [`.agent/SKILL.md`](.agent/SKILL.md) | FAQs técnicas, patrones de implementación |
