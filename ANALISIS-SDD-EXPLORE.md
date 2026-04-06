# Reporte de Auditoría Senior: SDD Explore — AgendaZonal

> **Fecha**: Abril 2026
> **Analista**: Antigravity (Senior System Analyst)
> **Alcance**: Revisión profunda de requerimientos vs. implementación real (Backend & Frontend)

---

## Metodología de Auditoría
Se han analizado en detalle todas las especificaciones (`SPECS/`) del proyecto, cruzándolas en doble vía con la implementación de **FastAPI** (`backend/`) y las interfaces **HTML/JS** (`frontend/`). A continuación, se presenta un mapeo exhaustivo de qué fue solicitado vs qué fue implementado, dónde se encuentra el código y cómo operarlo.

---

## Análisis y Verificación por Especificación

### 1. SPEC-001: Autenticación y Setup Base
**Estado de Verificación:** ✅ Implementado con brechas menores.

- **Descripción**: Sistema de login por JWT, registro (con CAPTCHA) y roles (user/moderator/admin).
- **Implementación Backend**: 
  - Rutas definidas en `backend/app/routes/auth.py` (`/api/auth/login`, `/api/auth/register`).
  - Lógica de token gestionada con esquema `Bearer` y dependencias de `database.py`.
- **Implementación Frontend**:
  - `frontend/login.html` y `frontend/register.html`. 
  - Consumido vía cliente JS en `frontend/js/api.js`. El JWT se guarda en el `localStorage` (como `token`).
- **Cómo usarlo**:  
  Cualquier usuario anónimo puede dirigirse a `/register` para tener una cuenta. En inicio de sesión satisfactorio (`/login`), JS intercepta el retorno y almacena el JWT inyectándolo luego en los headers de futuras peticiones autenticadas.
- **🚨 Alerta Analítica**:
  - La documentación menciona el endpoint `GET /api/auth/me` para obtener el contexto de sesión activo y `POST /api/auth/bootstrap-admin` para arrancar la base. **Ambos endpoints documentados no existen en el backend**.

---

### 2. SPEC-002: CRUD de Contactos (Directorio Base)
**Estado de Verificación:** ✅ Completamente Implementado.

- **Descripción**: Gestión de las fichas de proveedor (alta, edición, borrado) y búsqueda simple por texto.
- **Implementación Backend**: 
  - El grueso se ubica en `backend/app/routes/contacts.py` y `backend/app/models/contact.py`.
  - Capacidad nativa de búsqueda LIKE con escape.
- **Implementación Frontend**:
  - Los archivos clave son `frontend/add.html`, `frontend/edit.html` (formularios para proveedor/auth) y `frontend/search.html` (para el buscador final).
- **Cómo usarlo**: 
  - **Dueños**: Navegan al dashboard para gestionar sus operaciones en `/add` o `/edit`. Todo input invoca `fetch()` a la API y refresca su view o redirecciona. 
  - **Buscadores**: La barra de búsqueda global intercepta texto y redirige al listado que a su vez llama al motor textual.
- **🚨 Alerta Analítica**:
  - La API de exportación cruda en la ruta `/api/contacts/export` está desprotegida (acceso público), lo que representa un riesgo moderado de fuga completa de base de datos de proveedores.

---

### 3. SPEC-003: Evolución Hiperzonal (El Core de la app)
**Estado de Verificación:** ⚠️ Mayormente Implementado, pero con fallas de convergencia estructural.

Esta es la especificación más grande (geo-búsqueda, reseñas, WhatsApp, Panel PWA, Reportes).

#### A. Geo-Búsqueda & Mapas
- **Backend:** `backend/app/geo.py` y la ruta `/api/contacts/search` que recibe args `lat`, `lon`, `radius_km`. Utiliza lógica Math de bounding box para cálculos veloces pre-Fórmula de Haversine.
- **Frontend:** Implementado al 100%. `frontend/search.html` usa un toggle "Mapa/Lista" gobernado por `frontend/js/geo.js` con **Leaflet.js** y **MarkerCluster**.
- **Cómo usarlo:** El usuario presiona el botón de geolocalización. El browser lanza `navigator.geolocation`; si permite, el frontend envía `lat/lon` al endpoint y el backend retorna ítems filtrados por cercanía. Se agrupan visualmente al alejar el zoom.

#### B. Sistema de Reseñas y Moderación
- **Backend:** `backend/app/routes/reviews.py` con control estricto 1-reserva por usuario.
- **Frontend:** Visible y operable en `frontend/profile.html` (creación y lectura). Lógica administrativa en `frontend/admin-reviews.html`.
- **Cómo usarlo:** Todo visitante de un `profile` puede dejar Rating sobre un negocio. El panel del admin (`/admin/reviews`) carga aquellas pendienes ( `is_approved=false` ) para aceptarlas. Al aprobarla, un trigger o logica de servicio recalcula el promedio `avg_rating`.

#### C. Dashboard, Ofertas Flash y WhatsApp Leads
- **Backend:** `/api/provider/dashboard`, persistencia en `lead_events.py` y endpoints en `offers.py`. 
- **Frontend:** `frontend/dashboard.html` como panel del proveedor (muestra graficos y lista KPIs) y el botón flotante en `profile.html`.
- **Cómo usarlo:** En el modo visitante, si apretamos en el "WhatsApp", JS llama a `/api/contacts/{id}/leads` (para sumar un evento de tipo whatsapp) y luego dispara redirección a `wa.me/...`. 

#### D. PWA Instalable / Service Worker
- **Implementación Fronted:** Manifest expuesto (`manifest.json`) y worker configurado (`sw.js`). Cachea el layout principal y devuelve un `offline.html` al cortarse el internet.
- **🚨 Alerta Analítica (Severidad Alta): Notificaciones Push**
  - **Incompletitud Total:** El framework PWA tiene Service Worker pero la parte lógica de Push es defectuosa en Backend y Frontend. 
  - Backend tiene endpoints pero faltan dependencias crudas (`pywebpush` jamás instalada o referenciada en `requirements.txt`).
  - En backend falta inyectar las llaves **VAPID**.
  - El Frontend carece de la UI (botón, script) para suscribirse a un Push Manager.

#### E. Admin y Reportes Especiales (Moderador vs Crowdsource)
- **Implementación:** Admin interfaces en `/admin/...`. El CRUD de Utilidades (Farmacias) está operativo, así como Analytics (`/admin/analytics.html`).
- **🚨 Alerta Analítica:** Capacidad huérfana. El backend provee `POST /api/contacts/{id}/report` para los usuarios (usando la App) pero **NO existe** botón frontend "Reportar contacto" operante en `profile.html`.

---

### 4. SPEC-004: Mejoras Competitivas V3
**Estado de Verificación:** ✅ Implementado con alto estándar de UI.

- **Descripción**: Horarios enriquecidos, galerías de hasta 5 imágenes, RRSS, sugerencia de proximidad.
- **Implementación Backend**: `contacts.py` ahora expone `/api/contacts/{id}/photos`, `/schedules` y un endpoint de Machine-like-matching `/api/contacts/{id}/related`.
- **Implementación Frontend**:
  - `frontend/profile.html` orquesta carruseles CSS/Vanilla dinámicos sobre las limitadas fotos, lista redes (Instagram/Facebook) y el apartado "Negocios Similares Cerca".
- **Cómo usarlo**: 
  - **Proveedor:** Subiendo imágenes post-creación en su pantalla de dashboard, así como los slots estructurados (Lun-Dom). 
  - **Buscador:** Viendo "Más como este plomero" en la ficha, derivando a URLs amigables que interrcepan slugs y reenvían como `/c/{slug}`.

---

## 💡 Conclusión del Analista y Call to Action (Next Steps)

El sistema **está sumamente robusto para un lanzamiento MVP escalado**, la estructura SDD (Spec-Driven Development) ha sido muy prolija. Se recomiendan enfáticamente tres medidas inmediatas si el objetivo es pasar a Producción Real:

1. **Purga Documental y Endpointing:** Remover referencias de endpoints no creados (`/api/auth/me`) o construirlos; corregir urgéntemente la exposición pública masiva en el endpoint CSV `export` para visitantes libres (riesgo de scraping).
2. **UX Faltante (UI Ghosts):** Inyectar los botones frontend para la moderación comunitaria. Backend soporta "Reportar spam" (SPEC-003, Fase 5) pero los usuarios no tienen donde clickearlo.
3. **Decisión Push notifications:** O se elimina funcionalmente del `Service Worker` la falsa promesa de Push, o se instalan correctamente las dependencias (`pywebpush`) para no ensillar el sistema con promesas de API muertas al instalar dependencias.
