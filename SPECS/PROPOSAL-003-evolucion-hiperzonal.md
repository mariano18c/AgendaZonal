# PROPOSAL-003: Evolución Hiperzonal — AgendaZonal v2

## Metadata
- **Fecha**: 2026-03-29
- **Autor**: MarianoC
- **Estado**: pending_approval
- **Depende de**: SPEC-001 (Auth) ✅ | SPEC-002 (CRUD) ✅

## Overview
Evolución de AgendaZonal desde directorio estático hacia plataforma hiperzonal interactiva: geolocalización con SpatiaLite, sistema de reseñas, leads WhatsApp, ofertas flash, mapas interactivos, PWA offline, dashboard proveedor, y moderación avanzada. Stack: FastAPI + SQLite (SpatiaLite) + HTML/Tailwind/JS. Objetivo RPi 5 (4GB RAM).

## Motivation
AgendaZonal hoy es un directorio CRUD básico. Los vecinos necesitan encontrar proveedores CERCANOS, con CONFIABILIDAD (reseñas), y CONTACTARLOS fácilmente (WhatsApp). Los proveedores necesitan VISIBILIDAD y ANALYTICS.

## Alcance

### En Alcance (Fases 1-5)
| # | Feature | Fase |
|---|---------|------|
| 1 | SpatiaLite + búsqueda geo por radio | 1 |
| 2 | Mapas interactivos Leaflet/OSM | 1 |
| 3 | Geolocalización automática del usuario | 1 |
| 4 | Sistema de reseñas (rating 1-5 + comentario + foto) | 2 |
| 5 | Mejora verificación proveedor (niveles 1-3) | 2 |
| 6 | Moderación de reseñas por admin | 2 |
| 7 | Leads WhatsApp (deep links + tracking) | 3 |
| 8 | Ofertas flash con expiración | 3 |
| 9 | Dashboard proveedor (leads, reseñas, ofertas) | 3 |
| 10 | PWA (service worker + manifest + offline cache) | 4 |
| 11 | Rate limiting anti-spam | 4 |
| 12 | Admin: moderación proveedores + crowdsourced reports | 5 |
| 13 | Admin: analytics zonales + export CSV | 5 |
| 14 | Utilidades barrio (farmacias turno) | 5 |

### Fuera de Alcance
- IA Matching (pendiente para análisis futuro con API externa)
- QR Generator por perfil
- Carrito de compras / pagos
- WhatsApp Business API (solo deep links wa.me)
- AR / voz

## Enfoque Técnico

### Arquitectura: Stack Actual + Extensiones
- **NO migrar** a PostgreSQL: SpatiaLite da geo queries sobre SQLite
- **NO migrar** a Next.js/React: FastAPI + HTML/Tailwind/JS es suficiente
- Patrón: misma arquitectura actual (models → routes → schemas → frontend)

### Geo: SpatiaLite sobre SQLite
```
SQLite + mod_spatialite = geo queries sin servidor de DB
- ST_Distance_Sphere para cálculo de distancias
- Filtros por radio (5-50km)
- ~50MB RAM extra vs 600MB de PostgreSQL
- Escala hasta ~10k proveedores en RPi 5
```

### Mapas: Leaflet.js + OpenStreetMap (CDN)
```
- Leaflet.js desde CDN (mismo patrón que Tailwind CDN)
- OpenStreetMap tiles gratuitos (sin API key)
- Nominatim para geocoding inverso
- Marcadores de proveedores con popups
```

### Reseñas: Tabla nueva + moderación
```
- reviews: rating (1-5), comment, photo, is_approved
- Moderación por admin (approve/reject)
- Rating promedio cacheado en contacts.avg_rating
```

### WhatsApp: Deep Links + Tracking
```
- wa.me/{phone}?text={mensaje_precargado}
- Tabla lead_events para tracking
- Dashboard proveedor muestra leads por período
```

## Áreas Afectadas

| Área | Impacto | Descripción |
|------|---------|-------------|
| `backend/app/database.py` | Modificado | Inicializar SpatiaLite |
| `backend/app/models/contact.py` | Modificado | Agregar geo index, avg_rating, offers_count |
| `backend/app/models/` | Nuevo | review.py, offer.py, lead_event.py, report.py |
| `backend/app/routes/contacts.py` | Modificado | Search geo, filtros por radio |
| `backend/app/routes/` | Nuevo | reviews.py, offers.py, leads.py, admin_analytics.py |
| `backend/app/schemas/` | Nuevo | review.py, offer.py, lead.py |
| `backend/requirements.txt` | Modificado | Agregar spalite, slowapi, qrcode |
| `frontend/search.html` | Modificado | Mapa Leaflet, geo search, filtros |
| `frontend/` | Nuevo | profile.html (detalle proveedor), offer.html |
| `frontend/js/api.js` | Modificado | Geo params, reviews API, leads tracking |
| `frontend/sw.js` | Nuevo | Service Worker PWA |
| `frontend/manifest.json` | Nuevo | PWA manifest |

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|------------|
| SpatiaLite no disponible en RPi 5 | Baja | Fallback: cálculo distancia Haversine en Python |
| Performance geo queries en SQLite | Media | Índices espaciales + LIMIT en queries |
| Spam de reseñas | Alta | Moderación obligatoria antes de publicar |
| Datos GPS sensibles (privacidad) | Media | GPS opt-in, no almacenar por defecto, Ley 25.326 |
| Scope creep (muchas features) | Alta | Fases estrictas, MVP = Fases 1-3 |

## Plan de Rollback
1. Cada fase es independiente: se puede revertir sin afectar las anteriores
2. SpatiaLite es una extensión SQLite: si falla, el código fallback usa Haversine
3. Migraciones con Alembic: rollback de schema con `alembic downgrade -1`
4. Feature flags en .env: `ENABLE_GEO=false` desactiva geo sin tocar código

## Dependencias
- SpatiaLite (`mod_spatialite` library) — sistema operativo
- SQLAlchemy (ya instalado)
- Leaflet.js v1.9+ — CDN
- OpenStreetMap tiles — gratuito
- slowapi — rate limiting
- Alembic — migraciones de schema
- Pillow (ya instalado) — fotos de reseñas

## Criterios de Éxito
- [ ] Búsqueda geo retorna proveedores dentro de radio X km del usuario
- [ ] Mapa muestra marcadores de proveedores con popup de info
- [ ] Usuario puede crear reseña con rating + comentario + foto
- [ ] Admin puede aprobar/rechazar reseñas
- [ ] Click en WhatsApp abre chat con mensaje precargado
- [ ] Proveedor ve dashboard con leads y reseñas
- [ ] PWA funciona offline mostrando última búsqueda cacheada
- [ ] Rate limit bloquea >30 requests/minuto por IP
- [ ] Lighthouse PWA score >80
- [ ] Todos los tests existentes siguen pasando

---

**¿Procedo con la creación del SPEC-003 detallado?**
