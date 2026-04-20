# API Endpoints: AgendaZonal

## Autenticación (JWT HttpOnly Cookies)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/api/auth/register` | Public | Registro de usuario (Rate Limited) |
| POST | `/api/auth/login` | Public | Login (Retorna HttpOnly Cookie) |
| GET | `/api/auth/me` | User | Obtener perfil actual |
| POST | `/api/auth/logout` | User | Limpiar cookies de sesión |

## Contactos & Búsqueda

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/api/contacts` | Public | Listado paginado |
| GET | `/api/contacts/search` | Public | Search (Text + Geo + Category) |
| GET | `/api/contacts/{id}` | Public | Detalle de contacto |
| POST | `/api/contacts` | Auth | Crear contacto (Requiere aprobación) |
| PUT | `/api/contacts/{id}` | Owner | Actualizar datos |
| DELETE | `/api/contacts/{id}` | Owner/Admin | Eliminación (Soft-delete) |
| GET | `/api/contacts/{id}/related` | Public | Businesses en la misma zona/rubro |

## Reviews & Moderación

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/api/contacts/{id}/reviews` | Auth | Crear reseña (1 por usuario/contacto) |
| GET | `/api/contacts/{id}/reviews` | Public | Listado de reseñas aprobadas |
| POST | `/api/reviews/{id}/reply` | Owner | Responder a una reseña |
| PUT | `/api/admin/reviews/{id}/approve`| Mod+ | Moderar reseña |

## Flash Offers

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/api/contacts/{id}/offers` | Owner | Crear oferta flash |
| GET | `/api/contacts/{id}/offers` | Public | Listado de ofertas activas |

## Admin & Analytics

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/api/admin/analytics` | Mod+ | Estadísticas de la zona |
| GET | `/api/admin/analytics/export` | Admin | Exportar datos (CSV/JSON) |
| CRUD | `/api/admin/utilities` | Mod+ | Gestión de farmacias de turno/emergencias |

## System Health

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/health` | Public | Check DB Status & Disk Space (RPi Monitor) |