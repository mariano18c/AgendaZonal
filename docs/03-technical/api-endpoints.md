# API Endpoints Catalog: AgendaZonal

Todos los endpoints tienen el prefijo `/api` (ej: `https://agendazonal.ar/api/auth/login`).

---

## 1. Autenticación (`/auth`)

| Método | Endpoint | Permisos | Descripción |
|--------|----------|----------|-------------|
| POST | `/login` | Public | Inicia sesión y setea HttpOnly Cookie (JWT). |
| POST | `/register` | Public | Registro de nuevos usuarios/proveedores. |
| POST | `/logout` | Authenticated| Borra la cookie de sesión. |
| GET | `/me` | Authenticated| Retorna perfil del usuario actual. |

---

## 2. Directorio de Contactos (`/contacts`)

| Método | Endpoint | Permisos | Descripción |
|--------|----------|----------|-------------|
| GET | `/` | Public | Lista contactos paginados. |
| GET | `/search` | Public | Búsqueda por texto, rubro y **Geolocalización**. |
| GET | `/{id}` | Public | Detalle completo de un comercio. |
| POST | `/` | User+ | Crea un nuevo contacto (asociado al usuario). |
| PUT | `/{id}/edit` | Public* | Sugerir edición (buffer de moderación). |
| POST | `/{id}/image`| Owner/Adm | Sube foto de perfil (JPEG, max 5MB). |
| GET | `/export` | Adm/Mod | Exportación masiva (CSV/JSON). |

---

## 3. Interacción y PWA (`/notifications`, `/reviews`)

| Método | Endpoint | Permisos | Descripción |
|--------|----------|----------|-------------|
| POST | `/notifications/subscribe` | Authenticated | Registra suscripción Web Push (VAPID). |
| GET | `/offers` | Public | Lista ofertas flash activas. |
| POST | `/reviews` | Authenticated | Publica reseña (queda pendiente de moderación). |
| GET | `/reviews/{id}` | Public | Lista reseñas aprobadas para un contacto. |

---

## 4. Administración y Moderación (`/admin`)

| Método | Endpoint | Permisos | Descripción |
|--------|----------|----------|-------------|
| GET | `/admin/stats` | Admin | Dashboad de sistema (RAM, CPU, Usuarios). |
| POST | `/admin/verify/{id}` | Adm/Mod | Aprueba/Rechaza sugerencias de cambios. |
| GET | `/admin/reports` | Adm/Mod | Lista reportes de spam o contenido inapropiado. |
| DELETE| `/admin/users/{id}` | Admin | Suspensión definitiva de cuenta. |

---

## Notas Técnicas
- **Rate Limiting**: La mayoría de los endpoints de escritura tienen un límite de 10-30 peticiones por minuto (SlowAPI).
- **Formatos**: Entrada y salida en JSON (UTF-8).
- **Imágenes**: Procesadas en el servidor utilizando Pillow (redimensión y optimización).