# TASKS-003: Evolución Hiperzonal — Descomposición de Tareas

## Metadata
- **Creado**: 2026-03-29
- **Spec**: SPEC-003 | Design: DESIGN-003
- **Estado**: ✅ archived

---

## FASE 1: Geo-Búsqueda + Mapas (6 tareas)

### TASK-003-01: Migración de Schema + Nuevos Campos en Contact
**Estado:** pending | **Spec:** SPEC-003, AD-01, AD-03

**Descripción:** Agregar campos nuevos a la tabla contacts y crear el script de migración.

**Pasos:**
1. Crear `backend/migrate_v2.py` con ALTER TABLE statements
2. Agregar columnas: `avg_rating`, `review_count`, `verification_level`, `status`
3. Migrar datos: `is_verified` → `verification_level`
4. Crear índices: geo, status, verification, rating
5. Actualizar modelo `Contact` en `models/contact.py`
6. Actualizar schemas `ContactResponse` en `schemas/contact.py`
7. Agregar campo `distance_km` al schema de response (opcional, nullable)

**Verificación:**
- [ ] Script de migración corre sin errores sobre DB existente
- [ ] Contact model tiene nuevos campos
- [ ] Tests existentes pasan
- [ ] GET /api/contacts retorna nuevos campos

---

### TASK-003-02: Utilidades Geo (Haversine)
**Estado:** pending | **Spec:** DESIGN-003, AD-01

**Descripción:** Crear módulo de utilidades geográficas.

**Pasos:**
1. Crear `backend/app/geo.py`
2. Implementar `haversine_km(lat1, lon1, lat2, lon2) → float`
3. Implementar `bounding_box(center_lat, center_lon, radius_km) → (lat_min, lat_max, lon_min, lon_max)`
4. Implementar `filter_by_distance(results, center_lat, center_lon, radius_km) → list`
5. Crear tests en `tests/unit/test_geo.py`

**Verificación:**
- [ ] Haversine calcula correctamente (verificar con coordenadas conocidas)
- [ ] Bounding box retorna rangos correctos
- [ ] Tests unitarios pasan

---

### TASK-003-03: Endpoint de Búsqueda Geo
**Estado:** pending | **Spec:** SPEC-003, US-01

**Descripción:** Modificar el endpoint de búsqueda para soportar geolocalización.

**Pasos:**
1. Modificar `GET /api/contacts/search` en `routes/contacts.py`
2. Agregar parámetros: `lat`, `lon`, `radius_km` (default 10)
3. Si `lat` + `lon` presentes:
   a. Calcular bounding box
   b. Filtrar contacts por bounding box (WHERE lat BETWEEN... AND lon BETWEEN...)
   c. Aplicar filtro Haversine sobre resultado
   d. Ordenar por distancia
   e. Incluir `distance_km` en cada resultado
4. Mantener compatibilidad: si no hay lat/lon, comportamiento actual
5. Combinar con `q` y `category_id` si están presentes
6. Crear tests en `tests/integration/test_geo_search.py`

**Verificación:**
- [ ] Search sin geo funciona igual que antes
- [ ] Search con geo retorna solo proveedores dentro del radio
- [ ] Resultados ordenados por distancia
- [ ] distance_km presente en response
- [ ] Combinación con texto y categoría funciona
- [ ] Tests de integración pasan

---

### TASK-003-04: Mapa Interactivo en Search (Frontend)
**Estado:** pending | **Spec:** SPEC-003, US-02

**Descripción:** Agregar mapa Leaflet.js a la página de búsqueda.

**Pasos:**
1. Agregar Leaflet CSS/JS CDN a `search.html`
2. Agregar contenedor `div#map` con altura fija
3. Agregar toggle "Lista" / "Mapa"
4. Crear `frontend/js/geo.js` con:
   - `initMap(containerId, lat, lon, zoom)`
   - `addContactMarkers(contacts, map)`
   - `createPopupContent(contact)` (nombre, categoría, rating, botón WhatsApp)
5. Inicializar mapa al cargar search.html
6. Actualizar markers cuando cambian los resultados de búsqueda
7. Cluster de markers cuando hay >20 en zona pequeña (Leaflet.markercluster desde CDN)

**Verificación:**
- [ ] Mapa se renderiza correctamente
- [ ] Marcadores aparecen en ubicaciones correctas
- [ ] Click en marcador muestra popup con info
- [ ] Toggle lista/mapa funciona
- [ ] Responsive en mobile

---

### TASK-003-05: Geolocalización del Navegador
**Estado:** pending | **Spec:** SPEC-003, US-03

**Descripción:** Agregar botón de geolocalización automática.

**Pasos:**
1. Agregar botón "Usar mi ubicación" en search.html
2. Implementar `getUserLocation()` en `js/geo.js`
3. Al obtener GPS: setear lat/lon en parámetros de búsqueda
4. Mostrar indicador de carga mientras se obtiene GPS
5. Manejar errores: permiso denegado, timeout, no soportado
6. Mostrar coordenadas actuales como "Buscando cerca de: [barrio]"
7. GPS es opt-in (no auto-activar)

**Verificación:**
- [ ] Botón visible y accesible
- [ ] Solicita permiso al usuario
- [ ] Actualiza búsqueda con ubicación
- [ ] Error handling funciona (rechazo, timeout)
- [ ] No auto-activa GPS

---

### TASK-003-06: Página de Perfil Proveedor (Frontend Básico)
**Estado:** pending | **Spec:** SPEC-003, US-02

**Descripción:** Crear página de detalle de proveedor.

**Pasos:**
1. Crear `frontend/profile.html`
2. Leer `id` de query params
3. Llamar `GET /api/contacts/{id}` para obtener datos
4. Mostrar: nombre, categoría, dirección, teléfono, horarios, descripción, foto
5. Mostrar mapa mini con ubicación (Leaflet, zoom alto)
6. Agregar ruta `/profile` en `main.py`
7. Botones: Volver, Editar (si dueño), WhatsApp

**Verificación:**
- [ ] Perfil carga correctamente con datos del contacto
- [ ] Mapa mini muestra ubicación
- [ ] Links y botones funcionan
- [ ] Responsive en mobile

---

## FASE 2: Reseñas + Verificación (7 tareas)

### TASK-003-07: Modelo Review + Schema
**Estado:** pending | **Spec:** SPEC-003, US-04

**Descripción:** Crear modelo Review y schemas Pydantic.

**Pasos:**
1. Crear `backend/app/models/review.py` con modelo Review
2. Crear `backend/app/schemas/review.py` con:
   - `ReviewCreate` (rating, comment?, photo?)
   - `ReviewResponse` (id, contact_id, user_id, rating, comment, photo_path, is_approved, created_at)
   - `ReviewListResponse` (reviews[], total)
3. Agregar import en `models/__init__.py`
4. Actualizar script de migración para crear tabla reviews

**Verificación:**
- [ ] Modelo crea tabla correctamente
- [ ] Schemas validan correctamente
- [ ] UNIQUE(contact_id, user_id) funciona

---

### TASK-003-08: Endpoints CRUD de Reseñas
**Estado:** pending | **Spec:** SPEC-003, US-04, US-05

**Descripción:** Implementar endpoints de reseñas.

**Pasos:**
1. Crear `backend/app/routes/reviews.py`
2. Implementar `POST /api/contacts/{id}/reviews`:
   - Auth requerido
   - Validar rating (1-5)
   - Verificar que el contacto existe
   - Verificar UNIQUE constraint (una reseña por usuario por contacto)
   - is_approved=false por defecto
   - Si hay foto: validar JPEG, max 2MB, resize 800x800
   - Guardar foto en `uploads/images/review_{id}.jpg`
3. Implementar `GET /api/contacts/{id}/reviews`:
   - Público
   - Filtro is_approved=true
   - Paginación (20/page)
   - Incluir username del reviewer
4. Incluir router en `main.py`
5. Crear tests en `tests/integration/test_reviews.py`

**Verificación:**
- [ ] Crear reseña funciona
- [ ] Doble reseña del mismo usuario falla (409)
- [ ] Reseñas pendientes no aparecen en GET público
- [ ] Paginación funciona
- [ ] Foto se procesa correctamente
- [ ] Tests pasan

---

### TASK-003-09: Moderación de Reseñas (Admin)
**Estado:** pending | **Spec:** SPEC-003, US-07

**Descripción:** Endpoints de moderación para admin/mod.

**Pasos:**
1. Agregar a `routes/reviews.py`:
   - `GET /api/admin/reviews/pending` (mod+): lista reseñas pendientes
   - `POST /api/admin/reviews/{id}/approve` (mod+): aprueba y recalcula rating
   - `POST /api/admin/reviews/{id}/reject` (mod+): rechaza con razón opcional
2. Implementar recálculo de rating al aprobar:
   ```python
   def recalculate_rating(db, contact_id):
       approved = db.query(Review).filter(
           Review.contact_id == contact_id, Review.is_approved == True
       ).all()
       avg = sum(r.rating for r in approved) / len(approved) if approved else 0
       contact.avg_rating = round(avg, 1)
       contact.review_count = len(approved)
   ```
3. Crear tests de moderación

**Verificación:**
- [ ] Admin ve reseñas pendientes
- [ ] Aprobar actualiza avg_rating y review_count
- [ ] Rechazar no afecta estadísticas
- [ ] Rechazar reseña previamente aprobada recalcula

---

### TASK-003-10: Mostrar Reseñas en Perfil
**Estado:** pending | **Spec:** SPEC-003, US-05

**Descripción:** Integrar reseñas en la página de perfil.

**Pasos:**
1. En `profile.html`, agregar sección "Reseñas"
2. Mostrar rating promedio con estrellas (⭐ visual)
3. Mostrar cantidad de reseñas
4. Listar reseñas aprobadas con paginación
5. Cada reseña: estrellas, comentario, fecha, nombre usuario, foto (si hay)
6. Si usuario autenticado: mostrar formulario para crear reseña
   - Input: estrellas (click en 1-5), comentario (textarea), foto (file input)
   - Submit llama POST /api/contacts/{id}/reviews
7. Mostrar mensaje "pendiente de aprobación" tras crear

**Verificación:**
- [ ] Rating promedio se muestra correctamente
- [ ] Reseñas se listan con paginación
- [ ] Formulario de reseña funciona
- [ ] Foto se puede adjuntar
- [ ] Mensaje de pendiente aparece

---

### TASK-003-11: Mejora Verificación por Niveles
**Estado:** pending | **Spec:** SPEC-003, US-06

**Descripción:** Sistema de verificación en 3 niveles.

**Pasos:**
1. En modelo Contact, campo `verification_level` (0-3) ya creado en TASK-003-01
2. Agregar endpoint `PUT /api/admin/contacts/{id}/verification`:
   - Body: `{ verification_level: 0|1|2|3 }`
   - Auth: moderator/admin
3. Actualizar `schemas/contact.py` con `VerificationLevel` enum
4. En `profile.html`, mostrar badge según nivel:
   - 0: gris "Sin verificar"
   - 1: azul "Verificado"
   - 2: verde "Documentado"
   - 3: dorado "Premium"
5. Actualizar `POST /api/contacts/{id}/verify` para usar verification_level en vez de boolean
6. Mantener compatibilidad con `is_verified` (si is_verified=true → level≥1)

**Verificación:**
- [ ] Admin puede cambiar nivel de verificación
- [ ] Badge visual cambia según nivel
- [ ] is_verified sigue funcionando como campo legacy
- [ ] Tests pasan

---

### TASK-003-12: Frontend Admin de Reseñas
**Estado:** pending | **Spec:** SPEC-003, US-07

**Descripción:** Página de moderación de reseñas para admin.

**Pasos:**
1. Crear `frontend/admin-reviews.html`
2. Listar reseñas pendientes (más recientes primero)
3. Cada reseña: rating, comentario, foto (thumbnail), nombre contacto, nombre usuario, fecha
4. Botones: Aprobar, Rechazar (con campo de razón opcional)
5. Filtros: todas, pendientes, aprobadas
6. Agregar ruta `/admin/reviews` en `main.py`
7. Link en navbar para admin/mod

**Verificación:**
- [ ] Admin puede ver reseñas pendientes
- [ ] Aprobar funciona y quita de la lista
- [ ] Rechazar funciona con razón
- [ ] Filtros funcionan
- [ ] Solo visible para admin/mod

---

### TASK-003-13: Tests Fase 2
**Estado:** pending | **Spec:** SPEC-003

**Descripción:** Tests completos para la funcionalidad de reseñas.

**Pasos:**
1. `tests/integration/test_reviews.py`:
   - Crear reseña (auth)
   - Crear reseña sin auth (401)
   - Doble reseña mismo usuario (409)
   - Reseña con rating inválido (400)
   - Listar reseñas aprobadas (público)
   - Reseña pendiente no aparece en listado público
2. `tests/integration/test_review_moderation.py`:
   - Aprobar reseña (mod)
   - Aprobar reseña sin permisos (403)
   - Rechazar reseña (mod)
   - Recálculo de rating al aprobar
   - Recálculo al rechazar aprobada
3. `tests/integration/test_verification.py`:
   - Cambiar nivel verificación (admin)
   - Sin permisos (403)
   - Niveles inválidos (400)

**Verificación:**
- [ ] Todos los tests pasan
- [ ] Coverage de reseñas > 80%

---

## FASE 3: WhatsApp + Ofertas + Dashboard (7 tareas)

### TASK-003-14: Modelo Offer + Schema
**Estado:** pending | **Spec:** SPEC-003, US-10

**Descripción:** Crear modelo de ofertas flash.

**Pasos:**
1. Crear `backend/app/models/offer.py`
2. Crear `backend/app/schemas/offer.py`:
   - `OfferCreate` (title, description?, discount_pct?, expires_at)
   - `OfferResponse` (id, contact_id, title, description, discount_pct, expires_at, is_active, created_at)
3. Agregar import en `models/__init__.py`
4. Actualizar migración

**Verificación:**
- [ ] Modelo y schema validan correctamente
- [ ] discount_pct entre 1-99

---

### TASK-003-15: Endpoints CRUD de Ofertas
**Estado:** pending | **Spec:** SPEC-003, US-10

**Descripción:** CRUD de ofertas flash por contacto.

**Pasos:**
1. Crear `backend/app/routes/offers.py`
2. Implementar:
   - `POST /api/contacts/{id}/offers` (owner): crear oferta
   - `GET /api/contacts/{id}/offers` (público): listar activas (expires_at > now)
   - `PUT /api/contacts/{id}/offers/{oid}` (owner): editar
   - `DELETE /api/contacts/{id}/offers/{oid}` (owner): eliminar
3. Validaciones: title obligatorio, expires_at futuro, discount_pct 1-99
4. Incluir router en `main.py`
5. Tests

**Verificación:**
- [ ] CRUD funciona
- [ ] Solo dueño puede crear/editar/eliminar
- [ ] Ofertas expiradas no aparecen en GET público
- [ ] Tests pasan

---

### TASK-003-16: Modelo LeadEvent + Tracking WhatsApp
**Estado:** pending | **Spec:** SPEC-003, US-08, US-09

**Descripción:** Tracking de clicks en WhatsApp.

**Pasos:**
1. Crear `backend/app/models/lead_event.py`
2. Crear `backend/app/schemas/lead.py`
3. Implementar endpoints:
   - `POST /api/contacts/{id}/leads` (auth opcional): registrar click
   - `GET /api/contacts/{id}/leads` (owner): obtener leads del período
4. Response de GET leads: total, by_source, by_day (últimos 30 días)
5. Incluir router
6. Tests

**Verificación:**
- [ ] Click se registra correctamente
- [ ] Owner puede ver sus leads
- [ ] Estadísticas por día correctas
- [ ] Non-owner no puede ver leads de otro (403)

---

### TASK-003-17: Botón WhatsApp en Perfil
**Estado:** pending | **Spec:** SPEC-003, US-08

**Descripción:** Integrar WhatsApp deep link + tracking en perfil.

**Pasos:**
1. En `profile.html`, agregar botón prominente "Contactar por WhatsApp"
2. Al click:
   a. Registrar lead via POST /api/contacts/{id}/leads
   b. Abrir `https://wa.me/{phone}?text={mensaje}`
3. Mensaje pre-cargado: "Hola {nombre}, te encontré en AgendaZonal y quería consultar sobre..."
4. Funciona en móvil (app) y desktop (WhatsApp Web)
5. Botón con icono WhatsApp (SVG inline o CDN icon)

**Verificación:**
- [ ] Click abre WhatsApp con mensaje precargado
- [ ] Lead se registra antes de abrir WhatsApp
- [ ] Funciona en móvil y desktop
- [ ] Si no hay teléfono, botón no aparece

---

### TASK-003-18: Ofertas en Perfil
**Estado:** pending | **Spec:** SPEC-003, US-10

**Descripción:** Mostrar ofertas activas en perfil de proveedor.

**Pasos:**
1. En `profile.html`, agregar sección "Ofertas"
2. Card por oferta: título, descripción, descuento (si hay), countdown de expiración
3. Countdown visual: "Expira en X días Y horas" o "Expira mañana"
4. Ofertas expiradas no se muestran
5. Si es dueño: botones para crear/editar/eliminar ofertas

**Verificación:**
- [ ] Ofertas activas se muestran
- [ ] Countdown funciona
- [ ] CRUD desde perfil funciona para dueño
- [ ] Ofertas expiradas desaparecen automáticamente

---

### TASK-003-19: Dashboard Proveedor
**Estado:** pending | **Spec:** SPEC-003, US-11

**Descripción:** Panel de estadísticas para proveedores.

**Pasos:**
1. Crear endpoint `GET /api/provider/dashboard`:
   - Busca todos los contactos del usuario
   - Agrega: leads este mes, leads mes anterior, rating promedio, reseñas totales, ofertas activas
   - Leads por semana (últimas 4 semanas)
   - Reseñas recientes (últimas 10)
2. Crear `frontend/dashboard.html`:
   - Tarjetas de métricas
   - Gráfico simple de leads (SVG o Chart.js CDN)
   - Lista de reseñas recientes
3. Agregar ruta `/dashboard` en `main.py`
4. Link en navbar (si usuario tiene contactos)

**Verificación:**
- [ ] Dashboard muestra métricas correctas
- [ ] Gráfico de leads funciona
- [ ] Solo accesible si usuario tiene contactos
- [ ] Responsive

---

### TASK-003-20: Tests Fase 3
**Estado:** pending | **Spec:** SPEC-003

**Descripción:** Tests para ofertas, leads, dashboard.

**Pasos:**
1. `tests/integration/test_offers.py`: CRUD, expiración, permisos
2. `tests/integration/test_leads.py`: registro, visualización, permisos
3. `tests/integration/test_dashboard.py`: métricas correctas

**Verificación:**
- [ ] Todos los tests pasan
- [ ] Coverage > 80%

---

## FASE 4: PWA + Rate Limiting (4 tareas)

### TASK-003-21: Service Worker + PWA Manifest
**Estado:** pending | **Spec:** SPEC-003, US-12

**Descripción:** Configurar PWA básica.

**Pasos:**
1. Crear `frontend/manifest.json` con app info
2. Crear `frontend/sw.js` con estrategia network-first
3. Precache: todas las páginas HTML, api.js, app.js, geo.js
4. Runtime cache: responses de /api/contacts/search (stale-while-revalidate)
5. Crear `frontend/offline.html` con mensaje amigable
6. Registrar SW en todas las páginas HTML (script inline al final)
7. Agregar `<link rel="manifest">` en todos los HTML
8. Crear iconos básicos (192x192, 512x512) en `frontend/icons/`
9. Servir archivos estáticos en `main.py`

**Verificación:**
- [ ] SW se registra correctamente
- [ ] App funciona offline (muestra cache o offline.html)
- [ ] Lighthouse PWA score ≥ 80
- [ ] "Instalar app" aparece en Chrome mobile

---

### TASK-003-22: Rate Limiting Endpoints
**Estado:** pending | **Spec:** SPEC-003, US-13

**Descripción:** Aplicar rate limits a endpoints.

**Pasos:**
1. `rate_limit.py` ya existe con slowapi
2. Agregar decoradores `@limiter.limit()` a endpoints:
   - Auth (login): `10/minute`
   - Auth (register): `5/minute`
   - Search: `30/minute`
   - Create contact: `10/day`
   - Create review: `5/hour`
   - Global fallback: `60/minute`
3. Configurar headers X-RateLimit en responses
4. Tests de rate limiting

**Verificación:**
- [ ] Rate limits aplicados correctamente
- [ ] 429 response con mensaje claro
- [ ] Headers X-RateLimit presentes
- [ ] Tests verifican límites

---

### TASK-003-23: Íconos PWA
**Estado:** pending | **Spec:** SPEC-003, US-12

**Descripción:** Generar íconos para PWA.

**Pasos:**
1. Crear ícono simple 512x512 (diseño básico con "AZ" o similar)
2. Redimensionar a 192x192
3. Guardar en `frontend/icons/icon-192.png` y `icon-512.png`
4. Usar Pillow para generación programática si no hay asset

**Verificación:**
- [ ] Íconos existen en paths correctos
- [ ] Manifest referencia los paths correctos
- [ ] Íconos se muestran al instalar PWA

---

### TASK-003-24: Tests Fase 4
**Estado:** pending | **Spec:** SPEC-003

**Descripción:** Tests de PWA y rate limiting.

**Verificación:**
- [ ] Lighthouse PWA audit pasa
- [ ] Rate limiting tests pasan
- [ ] Offline behavior testeado

---

## FASE 5: Admin Avanzado + Utilidades (5 tareas)

### TASK-003-25: Modelo Report + Sistema de Reportes
**Estado:** pending | **Spec:** SPEC-003, US-14

**Descripción:** Sistema crowdsourced de reportes.

**Pasos:**
1. Crear `backend/app/models/report.py`
2. Crear `backend/app/schemas/report.py`
3. Implementar `POST /api/contacts/{id}/report` (auth):
   - UNIQUE(contact_id, user_id)
   - No puede reportarse a sí mismo
   - Al 3er reporte distinto → contact.status='flagged'
4. Implementar `GET /api/admin/reports/flagged` (mod+)
5. Implementar `POST /api/admin/reports/{id}/resolve` (mod+):
   - Actions: reactivate, suspend, delete
6. Tests

**Verificación:**
- [ ] Reportar funciona
- [ ] Auto-flag a las 3 denuncias
- [ ] Admin puede resolver
- [ ] Tests pasan

---

### TASK-003-26: Analytics Zonales + Export CSV
**Estado:** pending | **Spec:** SPEC-003, US-15

**Descripción:** Dashboard admin con métricas por zona.

**Pasos:**
1. Implementar `GET /api/admin/analytics`:
   - Params: zone (city/neighborhood), date_from, date_to
   - Métricas: proveedores activos, leads totales, rating promedio, reseñas, top categorías
2. Implementar `GET /api/admin/analytics/export`:
   - CSV con: zona, proveedor, leads_mes, rating, reseñas_count
3. Crear `frontend/admin-analytics.html`:
   - Tarjetas de métricas
   - Tabla de datos
   - Botón descargar CSV
4. Agregar ruta en `main.py`

**Verificación:**
- [ ] Métricas por zona correctas
- [ ] CSV se descarga con datos correctos
- [ ] Filtros de fecha funcionan

---

### TASK-003-27: Modelo UtilityItem + CRUD Utilidades
**Estado:** pending | **Spec:** SPEC-003, US-16

**Descripción:** CRUD de utilidades barrio (farmacias turno, etc).

**Pasos:**
1. Crear `backend/app/models/utility_item.py`
2. Crear `backend/app/schemas/utility.py`
3. Implementar endpoints:
   - `GET /api/utilities` (público): listar activas
   - `POST /api/admin/utilities` (admin): crear
   - `PUT /api/admin/utilities/{id}` (admin): editar
   - `DELETE /api/admin/utilities/{id}` (admin): eliminar (soft: is_active=false)
4. Crear `frontend/admin-utilities.html`: CRUD
5. En `index.html`: sección "Utilidades del Barrio"

**Verificación:**
- [ ] CRUD admin funciona
- [ ] Pública lista solo activas
- [ ] Landing muestra utilidades

---

### TASK-003-28: Admin Pages (Reports + Navbar)
**Estado:** pending | **Spec:** SPEC-003, US-14

**Descripción:** Páginas admin restantes y navbar actualizada.

**Pasos:**
1. Crear `frontend/admin-reports.html`:
   - Lista de proveedores flagged
   - Reportes por proveedor
   - Acciones: reactivar, suspender, eliminar
2. Actualizar navbar en `frontend/js/app.js`:
   - Agregar links: Dashboard, Admin Reseñas, Admin Reportes, Admin Analytics, Admin Utilidades
   - Mostrar solo según rol
3. Agregar todas las rutas nuevas en `main.py`

**Verificación:**
- [ ] Admin pages accesibles solo por rol correcto
- [ ] Navbar muestra links según rol
- [ ] Todas las rutas funcionan

---

### TASK-003-29: Tests Fase 5
**Estado:** pending | **Spec:** SPEC-003

**Descripción:** Tests finales del proyecto.

**Verificación:**
- [ ] Tests de reportes pasan
- [ ] Tests de analytics pasan
- [ ] Tests de utilidades pasan
- [ ] Tests de integración completa pasan
- [ ] Coverage total del proyecto > 80%

---

## Resumen de Tareas

| Fase | Tareas | Estimación |
|------|--------|-----------|
| 1: Geo + Mapas | 6 (01-06) | 2-3 sesiones |
| 2: Reseñas | 7 (07-13) | 2-3 sesiones |
| 3: WhatsApp + Ofertas | 7 (14-20) | 2-3 sesiones |
| 4: PWA + Rate Limit | 4 (21-24) | 1-2 sesiones |
| 5: Admin + Utilidades | 5 (25-29) | 2 sesiones |
| **TOTAL** | **29 tareas** | **9-13 sesiones** |

## Orden de Ejecución Recomendado

1. TASK-003-01 (migración schema) — **PRIMERO, todo depende de esto**
2. TASK-003-02 (geo utils)
3. TASK-003-03 (geo search endpoint)
4. TASK-003-04 (mapa frontend)
5. TASK-003-05 (geolocalización)
6. TASK-003-06 (perfil básico)
7. Luego continuar con Fase 2 → 3 → 4 → 5 en orden
