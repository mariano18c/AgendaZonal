# Database Schema: AgendaZonal

## Visión General
El sistema utiliza **SQLite** (WAL mode) con un esquema relacional de 14 tablas. A continuación se detallan las tablas principales y sus campos técnicos.

---

### 1. Tablas Core

#### 1.1 `users`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| username | VARCHAR(50) | UNIQUE |
| email | VARCHAR(255) | UNIQUE |
| phone_area_code | VARCHAR(5) | |
| phone_number | VARCHAR(20) | |
| password_hash | VARCHAR(255) | bcrypt |
| role | VARCHAR(20) | admin, moderator, user |
| is_active | BOOLEAN | Default True |
| created_at | DATETIME | |

#### 1.2 `contacts`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| name | VARCHAR(100) | |
| slug | VARCHAR(200) | UNIQUE, URL Friendly |
| user_id | INTEGER FK | Propietario |
| category_id | INTEGER FK | |
| phone | VARCHAR(20) | |
| email | VARCHAR(255) | |
| address | VARCHAR(255) | |
| latitude | FLOAT | |
| longitude | FLOAT | |
| description | VARCHAR(500) | |
| about | TEXT | Markdown support |
| status | VARCHAR(20) | active, flagged, suspended |
| verification_level| INTEGER | 0-3 |
| avg_rating | FLOAT | Cacheado |
| review_count | INTEGER | Cacheado |
| instagram | VARCHAR(100) | |
| facebook | VARCHAR(255) | |
| created_at | DATETIME | |

---

### 2. Tablas de Interacción

#### 2.1 `reviews`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| contact_id | INTEGER FK | |
| user_id | INTEGER FK | |
| rating | INTEGER | 1-5 |
| comment | TEXT | |
| is_approved | BOOLEAN | Moderado |
| reply_text | TEXT | Respuesta del owner |

#### 2.2 `offers` (Flash Offers)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| contact_id | INTEGER FK | |
| title | VARCHAR(200) | |
| discount_pct | INTEGER | 1-99 |
| expires_at | DATETIME | |
| is_active | BOOLEAN | |

---

### 3. Utilidades y Operaciones

#### 3.1 `utility_items`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| type | VARCHAR(20) | farmacia, emergencia, etc. |
| name | VARCHAR(200) | |
| phone | VARCHAR(20) | |
| is_active | BOOLEAN | |

#### 3.2 `notifications`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| user_id | INTEGER FK | |
| type | VARCHAR(50) | push, in-app |
| message | VARCHAR(500) | |
| is_read | BOOLEAN | |

---

## Índices Críticos
- `idx_contacts_geo`: (latitude, longitude) para Bounding Box pre-filter.
- `idx_contacts_slug`: Búsqueda rápida de perfiles.
- `idx_reviews_contact_approved`: Para cargar rápidamente el feed de reseñas.