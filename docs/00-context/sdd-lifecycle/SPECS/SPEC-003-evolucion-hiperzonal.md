# SPEC-003: Evolución Hiperzonal

## Metadata
- **Creado**: 2026-03-29
- **Archivado**: 2026-04-02
- **Autor**: MarianoC
- **Estado**: ✅ archived
- **Depende de**: SPEC-001 (Auth) ✅ | SPEC-002 (CRUD) ✅

## Overview
Evolución completa de AgendaZonal: geo-búsqueda, reseñas, WhatsApp, ofertas, mapas, PWA, dashboard proveedor, y moderación avanzada.

---

## Requisitos Funcionales

### FASE 1: Geo-Búsqueda + Mapas

#### US-01: Búsqueda por Geolocalización
**Como** vecino/buscardor
**Quiero** buscar proveedores cerca de mi ubicación
**Para** encontrar servicios rápidamente sin importar en qué barrio estoy

**Aceptación:**
- [ ] GET `/api/contacts/search` acepta parámetros `lat`, `lon`, `radius_km` (default 10)
- [ ] Retorna proveedores dentro del radio, ordenados por distancia
- [ ] Cada resultado incluye `distance_km` calculado
- [ ] Filtro combinable con `q` (texto) y `category_id`
- [ ] Si no se provee lat/lon, funciona igual que hoy (búsqueda texto)

#### US-02: Mapa Interactivo
**Como** buscardor
**Quiero** ver proveedores en un mapa interactivo
**Para** entender visualmente dónde están los servicios

**Aceptación:**
- [ ] Página de búsqueda tiene toggle "Lista" / "Mapa"
- [ ] Mapa usa Leaflet.js + OpenStreetMap tiles
- [ ] Marcadores por cada proveedor con lat/lng
- [ ] Click en marcador muestra popup: nombre, categoría, rating, botón WhatsApp
- [ ] Mapa centra en ubicación del usuario (si GPS disponible)
- [ ] Cluster de marcadores cuando hay muchos en zona pequeña

#### US-03: Geolocalización Automática
**Como** buscardor en móvil
**Quiero** que la app detecte mi ubicación automáticamente
**Para** no tener que escribir mi dirección

**Aceptación:**
- [ ] Botón "Usar mi ubicación" en búsqueda
- [ ] Usa `navigator.geolocation.getCurrentPosition()`
- [ ] Muestra indicador de carga mientras obtiene GPS
- [ ] Fallback graceful si usuario rechaza permiso GPS
- [ ] GPS es OPT-IN (no se activa automáticamente)

---

### FASE 2: Reseñas + Verificación

#### US-04: Crear Reseña
**Como** usuario que contactó un proveedor
**Quiero** dejar una reseña con rating y comentario
**Para** ayudar a otros vecinos a decidir

**Aceptación:**
- [ ] POST `/api/contacts/{id}/reviews` (auth requerido)
- [ ] Campos obligatorios: `rating` (1-5)
- [ ] Campos opcionales: `comment` (max 500 chars), `photo` (JPEG, max 2MB)
- [ ] Un usuario solo puede reseñar un proveedor UNA vez
- [ ] Reseña queda en estado `is_approved=false` (pendiente moderación)
- [ ] Usuario ve mensaje "Tu reseña está pendiente de aprobación"

#### US-05: Ver Reseñas en Perfil
**Como** buscardor
**Quiero** ver las reseñas de un proveedor
**Para** evaluar su calidad antes de contactarlo

**Aceptación:**
- [ ] GET `/api/contacts/{id}/reviews` retorna reseñas aprobadas
- [ ] Cada reseña muestra: rating (estrellas), comentario, fecha, nombre usuario
- [ ] Rating promedio mostrado en el perfil del proveedor
- [ ] Cantidad total de reseñas visible
- [ ] Reseñas paginadas (20 por página)

#### US-06: Mejora Verificación Proveedor
**Como** admin/moderador
**Quiero** asignar niveles de verificación a proveedores
**Para** que los vecinos distingan proveedores confiables

**Aceptación:**
- [ ] Campo `verification_level` en contacts: 0=sin verificar, 1=básico, 2=documentado, 3=premium
- [ ] Nivel 1: verificación básica (email/teléfono confirmado)
- [ ] Nivel 2: documentado (fotos del local/proyectos, CUIT verificado)
- [ ] Nivel 3: premium (inspección presencial o reputación comprobada)
- [ ] Badge visual diferente por nivel (color/forma)
- [ ] Solo admin/mod puede cambiar nivel

#### US-07: Moderación de Reseñas
**Como** admin/moderador
**Quiero** aprobar o rechazar reseñas antes de que sean públicas
**Para** mantener calidad y evitar spam

**Aceptación:**
- [ ] GET `/api/admin/reviews/pending` lista reseñas pendientes
- [ ] POST `/api/admin/reviews/{id}/approve` aprueba reseña
- [ ] POST `/api/admin/reviews/{id}/reject` rechaza con razón opcional
- [ ] Al aprobar, se recalcula `avg_rating` y `review_count` del contacto
- [ ] Badge de moderador requerido

---

### FASE 3: WhatsApp + Ofertas + Dashboard

#### US-08: Contacto por WhatsApp
**Como** buscardor
**Quiero** contactar un proveedor por WhatsApp con un click
**Para** comunicarme rápidamente sin copiar números

**Aceptación:**
- [ ] Botón "Contactar por WhatsApp" en perfil de proveedor
- [ ] Deep link: `https://wa.me/{phone}?text={mensaje_precargado}`
- [ ] Mensaje incluye nombre del proveedor y espacio para consulta
- [ ] Click registra evento en `lead_events` (tracking)
- [ ] Funciona tanto en móvil como desktop (WhatsApp Web)

#### US-09: Tracking de Leads
**Como** proveedor
**Quiero** ver cuántos leads recibo por WhatsApp
**Para** medir la efectividad de mi perfil

**Aceptación:**
- [ ] Cada click en WhatsApp registra: contact_id, timestamp, source='whatsapp'
- [ ] GET `/api/contacts/{id}/leads` (auth, solo dueño) retorna leads del mes
- [ ] Contador de leads en dashboard proveedor

#### US-10: Ofertas Flash
**Como** proveedor
**Quiero** crear ofertas temporales con descuento
**Para** atraer más clientes

**Aceptación:**
- [ ] POST `/api/contacts/{id}/offers` crea oferta (auth, solo dueño)
- [ ] Campos: `title`, `description`, `discount_pct` (opcional), `expires_at`
- [ ] Oferta expirada no se muestra (filtro automático)
- [ ] PUT/DELETE para editar/eliminar ofertas propias
- [ ] Mostrar ofertas activas en perfil del proveedor
- [ ] Countdown visual ("expira en X horas")

#### US-11: Dashboard Proveedor
**Como** proveedor registrado
**Quiero** ver un panel con mis estadísticas
**Para** entender cómo les va a mis servicios

**Aceptación:**
- [ ] GET `/api/provider/dashboard` (auth) retorna resumen
- [ ] Métricas: leads este mes, leads mes anterior, rating promedio, reseñas totales, ofertas activas
- [ ] Gráfico simple de leads por semana (últimas 4 semanas)
- [ ] Lista de reseñas recientes con posibilidad de responder
- [ ] Solo accesible si el usuario tiene al menos un contacto creado

---

### FASE 4: PWA + Rate Limiting

#### US-12: PWA Instalable
**Como** usuario frecuente
**Quiero** instalar la app en mi teléfono
**Para** accederla rápido como si fuera una app nativa

**Aceptación:**
- [ ] `manifest.json` con nombre, iconos, theme_color, start_url
- [ ] Service Worker registra y activa correctamente
- [ ] Caché de assets estáticos (HTML, CSS, JS, iconos)
- [ ] Caché de última búsqueda (offline muestra resultados cacheados)
- [ ] Badge "Instalar app" visible en navegadores compatibles
- [ ] Lighthouse PWA score ≥ 80

#### US-13: Rate Limiting
**Como** sistema
**Quiero** limitar requests por IP
**Para** prevenir abuso y spam

**Aceptación:**
- [ ] Límite global: 60 requests/minuto por IP
- [ ] Límite auth endpoints: 10 requests/minuto por IP
- [ ] Límite reseñas: 5/hora por usuario
- [ ] Límite creación contactos: 10/día por usuario
- [ ] Respuesta 429 con mensaje claro cuando se excede
- [ ] Headers `X-RateLimit-*` en cada respuesta

---

### FASE 5: Admin Avanzado + Utilidades

#### US-14: Moderación de Proveedores (Crowdsourced)
**Como** usuario
**Quiero** reportar un proveedor con problema
**Para** mantener la calidad del directorio

**Aceptación:**
- [ ] POST `/api/contacts/{id}/report` crea reporte (auth)
- [ ] Campos: `reason` (select: spam, falso, inapropiado, cerrado), `details` (opcional)
- [ ] 3 reportes distintos → contacto pasa a `status='flagged'` automáticamente
- [ ] Admin ve lista de flagged y puede: reactivar, suspender, eliminar
- [ ] Usuario no puede reportar el mismo contacto dos veces

#### US-15: Analytics Zonales + Export
**Como** admin
**Quiero** ver estadísticas por zona y exportar datos
**Para** entender el uso de la plataforma

**Aceptación:**
- [ ] GET `/api/admin/analytics?zone=...` retorna métricas por zona
- [ ] Métricas: proveedores activos, leads totales, rating promedio, reseñas del período
- [ ] GET `/api/admin/analytics/export?format=csv` descarga CSV
- [ ] Campos CSV: zona, proveedor, leads_mes, rating, reseñas_count
- [ ] Filtros por fecha (desde/hasta)

#### US-16: Utilidades Barrio
**Como** residente
**Quiero** ver info útil de mi barrio (farmacias de turno)
**Para** tener datos prácticos del día a día

**Aceptación:**
- [ ] Sección "Utilidades" en landing page
- [ ] Farmacias de turno: muestra farmacias con horario de guardia
- [ ] Datos manuales por admin (no requiere integración externa inicial)
- [ ] Tabla simple: nombre, dirección, horario, teléfono
- [ ] Admin puede CRUD de utilidades desde panel

---

## Requisitos No Funcionales

| Requisito | Especificación |
|-----------|---------------|
| Performance | Búsqueda geo < 500ms para 1000 proveedores |
| Performance | Carga de mapa < 2s (tiles OSM) |
| Performance | Página perfil proveedor < 1s |
| Seguridad | GPS opt-in, nunca auto-activar |
| Seguridad | Rate limiting en todos los endpoints públicos |
| Seguridad | Reseñas moderadas antes de publicar |
| Seguridad | Ley 25.326 (datos personales Argentina) |
| Accesibilidad | WCAG 2.1 AA mínimo |
| Responsive | Mobile-first, funciona desde 320px |
| Compatibilidad | Chrome, Firefox, Safari, Edge (últimas 2 versiones) |
| Offline | PWA cachea última búsqueda y perfil visto |
| Plataforma | RPi 5 (4GB RAM), Linux aarch64 |

## Nuevos Modelos de Datos

### Review
```
reviews:
  id              INTEGER PK
  contact_id      INTEGER FK contacts.id NOT NULL
  user_id         INTEGER FK users.id NOT NULL
  rating          INTEGER NOT NULL (1-5)
  comment         TEXT (max 500)
  photo_path      VARCHAR(500)
  is_approved     BOOLEAN DEFAULT false
  approved_by     INTEGER FK users.id
  approved_at     DATETIME
  created_at      DATETIME DEFAULT now()
  UNIQUE(contact_id, user_id)  -- un usuario, una reseña por contacto
```

### Offer
```
offers:
  id              INTEGER PK
  contact_id      INTEGER FK contacts.id NOT NULL
  title           VARCHAR(200) NOT NULL
  description     VARCHAR(500)
  discount_pct    INTEGER (1-99, nullable)
  expires_at      DATETIME NOT NULL
  is_active       BOOLEAN DEFAULT true
  created_at      DATETIME DEFAULT now()
```

### LeadEvent
```
lead_events:
  id              INTEGER PK
  contact_id      INTEGER FK contacts.id NOT NULL
  user_id         INTEGER FK users.id (nullable, NULL=anónimo)
  source          VARCHAR(20) NOT NULL (whatsapp, phone, email)
  created_at      DATETIME DEFAULT now()
```

### Report
```
reports:
  id              INTEGER PK
  contact_id      INTEGER FK contacts.id NOT NULL
  user_id         INTEGER FK users.id NOT NULL
  reason          VARCHAR(20) NOT NULL (spam, falso, inapropiado, cerrado)
  details         TEXT (nullable)
  is_resolved     BOOLEAN DEFAULT false
  resolved_by     INTEGER FK users.id
  resolved_at     DATETIME
  created_at      DATETIME DEFAULT now()
  UNIQUE(contact_id, user_id)  -- un usuario, un reporte por contacto
```

### UtilityItem
```
utility_items:
  id              INTEGER PK
  type            VARCHAR(20) NOT NULL (farmacia_turno, emergencia, otro)
  name            VARCHAR(200) NOT NULL
  address         VARCHAR(255)
  phone           VARCHAR(20)
  schedule        VARCHAR(200)
  lat             FLOAT
  lon             FLOAT
  city            VARCHAR(100)
  is_active       BOOLEAN DEFAULT true
  created_by      INTEGER FK users.id
  created_at      DATETIME DEFAULT now()
  updated_at      DATETIME DEFAULT now()
```

## Cambios a Modelos Existentes

### Contact (campos nuevos)
```
avg_rating        FLOAT DEFAULT 0         -- cacheado al aprobar reseña
review_count      INTEGER DEFAULT 0       -- cacheado
verification_level INTEGER DEFAULT 0      -- 0=sin_verificar, 1=básico, 2=documentado, 3=premium
status            VARCHAR(20) DEFAULT 'active'  -- active, flagged, suspended
```

### Contact (campos existentes a reutilizar)
```
latitude          FLOAT (ya existe)       -- se usa para geo queries
longitude         FLOAT (ya existe)       -- se usa para geo queries
is_verified       BOOLEAN (ya existe)     -- migrar a verification_level
```

## Nuevos Endpoints

| Método | Ruta | Auth | Fase | Descripción |
|--------|------|------|------|-------------|
| GET | `/api/contacts/search` | Público | 1 | + lat, lon, radius_km params |
| GET | `/api/contacts/{id}/reviews` | Público | 2 | Reseñas aprobadas |
| POST | `/api/contacts/{id}/reviews` | Auth | 2 | Crear reseña |
| GET | `/api/admin/reviews/pending` | Mod+ | 2 | Reseñas pendientes |
| POST | `/api/admin/reviews/{id}/approve` | Mod+ | 2 | Aprobar reseña |
| POST | `/api/admin/reviews/{id}/reject` | Mod+ | 2 | Rechazar reseña |
| PUT | `/api/admin/contacts/{id}/verification` | Mod+ | 2 | Cambiar nivel verificación |
| GET | `/api/contacts/{id}/leads` | Owner | 3 | Leads del proveedor |
| POST | `/api/contacts/{id}/leads` | Público | 3 | Registrar click WhatsApp |
| GET | `/api/contacts/{id}/offers` | Público | 3 | Ofertas activas |
| POST | `/api/contacts/{id}/offers` | Owner | 3 | Crear oferta |
| PUT | `/api/contacts/{id}/offers/{oid}` | Owner | 3 | Editar oferta |
| DELETE | `/api/contacts/{id}/offers/{oid}` | Owner | 3 | Eliminar oferta |
| GET | `/api/provider/dashboard` | Auth | 3 | Dashboard proveedor |
| POST | `/api/contacts/{id}/report` | Auth | 5 | Reportar proveedor |
| GET | `/api/admin/reports/flagged` | Mod+ | 5 | Proveedores reportados |
| POST | `/api/admin/reports/{id}/resolve` | Mod+ | 5 | Resolver reporte |
| GET | `/api/admin/analytics` | Mod+ | 5 | Analytics zonales |
| GET | `/api/admin/analytics/export` | Mod+ | 5 | Export CSV |
| GET | `/api/utilities` | Público | 5 | Lista utilidades |
| POST | `/api/admin/utilities` | Admin | 5 | Crear utilidad |
| PUT | `/api/admin/utilities/{id}` | Admin | 5 | Editar utilidad |
| DELETE | `/api/admin/utilities/{id}` | Admin | 5 | Eliminar utilidad |

## Páginas Frontend Nuevas/Modificadas

| Página | URL | Fase | Estado |
|--------|-----|------|--------|
| Search (mejorada) | `/search` | 1 | Modificada: mapa, geo, filtros |
| Perfil Proveedor | `/profile?id={id}` | 1-3 | Nueva: detalle completo + reseñas + ofertas + WhatsApp |
| Dashboard Proveedor | `/dashboard` | 3 | Nueva: estadísticas proveedor |
| Admin Reseñas | `/admin/reviews` | 2 | Nueva: moderación reseñas |
| Admin Reports | `/admin/reports` | 5 | Nueva: moderación proveedores |
| Admin Analytics | `/admin/analytics` | 5 | Nueva: reportes + export |
| Admin Utilidades | `/admin/utilities` | 5 | Nueva: CRUD utilidades barrio |

---

## Criterios de Aceptación Globales

- [ ] Todos los endpoints existentes siguen funcionando (no breaking changes)
- [ ] Tests existentes pasan sin modificaciones
- [ ] Nuevos endpoints tienen tests unitarios e integración
- [ ] Frontend responsive funciona en 320px a 1920px
- [ ] Lighthouse Performance ≥ 85
- [ ] Lighthouse PWA ≥ 80 (post Fase 4)
- [ ] No hay regresiones de seguridad (SQLi, XSS, CSRF)
