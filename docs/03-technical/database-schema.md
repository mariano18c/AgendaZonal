# Database Schema: AgendaZonal (Complete)

El sistema utiliza **SQLite** (WAL mode) con un esquema relacional optimizado para alto rendimiento en Raspberry Pi 5.

---

## 1. Tablas de Identidad y Base

### 1.1 `users`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| username | VARCHAR(50) | UNIQUE |
| email | VARCHAR(255) | UNIQUE |
| password_hash | VARCHAR(255) | bcrypt |
| role | VARCHAR(20) | admin, moderator, user |
| is_active | BOOLEAN | Default True |
| created_at | DATETIME | |

### 1.2 `categories`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| code | INTEGER | UNIQUE, Código de rubro |
| name | VARCHAR(100) | UNIQUE |
| icon | VARCHAR(50) | Icono descriptivo |

---

## 2. Núcleo del Directorio

### 2.1 `contacts`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| name | VARCHAR(100) | |
| slug | VARCHAR(200) | UNIQUE, URL Friendly |
| user_id | INTEGER FK | Propietario (User) |
| category_id | INTEGER FK | FK a `categories` |
| phone | VARCHAR(20) | |
| latitude / longitude | FLOAT | Ubicación Geo |
| verification_level | INTEGER | 0=No verif, 1=Básico, 2=Premium, 3=Gold |
| status | VARCHAR(20) | active, flagged, suspended |

### 2.2 `contact_photos`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| contact_id | INTEGER FK | FK a `contacts` (ON DELETE CASCADE) |
| photo_path | VARCHAR(500) | Ruta en el FileSystem |
| caption | VARCHAR(200) | |
| sort_order | INTEGER | Orden de visualización |

### 2.3 `schedules`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| contact_id | INTEGER FK | FK a `contacts` |
| day_of_week | INTEGER | 0 (Lunes) a 6 (Domingo) |
| open_time / close_time | VARCHAR(5) | Formato "HH:MM" o NULL |

---

## 3. Interacción y Conversión

### 3.1 `reviews`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| contact_id | INTEGER FK | |
| user_id | INTEGER FK | |
| rating | INTEGER | 1 a 5 |
| comment | TEXT | |
| is_approved | BOOLEAN | Control de moderación |

### 3.2 `offers` (Flash Offers)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| contact_id | INTEGER FK | |
| title | VARCHAR(200) | |
| discount_pct | INTEGER | |
| expires_at | DATETIME | |

### 3.3 `lead_events`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| contact_id | INTEGER FK | |
| source | VARCHAR(20) | "whatsapp", "call", "web" |
| created_at | DATETIME | |

---

## 4. Moderación y Calidad

### 4.1 `contact_changes` (Borradores)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| contact_id | INTEGER FK | |
| field_name | VARCHAR(50) | Campo modificado |
| old_value / new_value | TEXT | Cambio propuesto |
| is_verified | BOOLEAN | Estado de la aprobación |

### 4.2 `reports`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| contact_id | INTEGER FK | |
| reason | VARCHAR(20) | spam, falso, inapropiado, cerrado |
| is_resolved | BOOLEAN | |

---

## 5. Utilidades y Operaciones

### 5.1 `utility_items` (Emergencias)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| type | VARCHAR(20) | farmacia_turno, emergencia, otro |
| name | VARCHAR(200) | |
| is_priority | BOOLEAN | |

### 5.2 `push_subscriptions`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | INTEGER PK | |
| endpoint | VARCHAR(500) | Browsing service endpoint |
| p256dh / auth | VARCHAR | VAPID Keys |
| city | VARCHAR(100) | Zona geográfica focalizada |

---

## Índices Críticos
- `idx_contacts_geo`: (latitude, longitude) - Bounding Box Pre-filter.
- `idx_photos_contact_order`: (contact_id, sort_order) - Carga de galería.
- `idx_leads_date`: (created_at) - Generación de estadísticas.
- `idx_reports_unresolved`: (is_resolved) - Cola de moderación.