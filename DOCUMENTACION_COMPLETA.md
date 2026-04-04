# Documentación Completa del Proyecto Agenda Comunitaria (AgendaZonal)

## Tabla de Contenidos
1. [Información General](#información-general)
2. [Stack Tecnológico](#stack-tecnológico)
3. [Estructura del Proyecto](#estructura-del-proyecto)
4. [Base de Datos](#base-de-datos)
5. [API Endpoints](#api-endpoints)
6. [Modelos de Datos](#modelos-de-datos)
7. [Categorías Predefinidas](#categorías-predefinidas)
8. [Datos de Contactos](#datos-de-contactos)
9. [Scripts de Importación](#scripts-de-importación)
10. [Configuración Regional](#configuración-regional)
11. [Cómo Ejecutar](#cómo-ejecutar)
12. [Historial de Desarrollo](#historial-de-desarrollo)

---

## Información General

| Campo | Valor |
|-------|-------|
| **Nombre del Proyecto** | Agenda Comunitaria / AgendaZonal |
| **Tipo** | Sistema web completo |
| **Plataforma** | Raspberry Pi 5 (4GB RAM) |
| **Estado** | ✅ COMPLETADO |
| **Idioma** | Español (Español Rioplatense) |
| **Zona Horaria** | America/Argentina/Buenos_Aires |
| **Zona de Cobertura** | Ybarlucea / Ibarlucea (radio 20km) |

---

## Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| **Backend** | FastAPI (Python) |
| **Base de Datos** | SQLite |
| **Frontend** | HTML + Tailwind CSS (CDN) + Vanilla JS |
| **Autenticación** | JWT (JSON Web Tokens) |
| **Servidor** | Uvicorn |

---

## Estructura del Proyecto

```
AgendaZonal/
├── AGENTS.md                    # Configuración de agentes IA
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # Punto de entrada FastAPI
│   │   ├── auth.py              # Autenticación JWT
│   │   ├── captcha.py           # Gestión de CAPTCHA
│   │   ├── config.py            # Configuración
│   │   ├── database.py          # Conexión SQLite
│   │   ├── geo.py               # Funciones geográficas
│   │   ├── rate_limit.py        # Limitación de tasa
│   │   ├── settings.py           # Configuración de settings
│   │   ├── models/              # Modelos SQLAlchemy
│   │   │   ├── __init__.py
│   │   │   ├── category.py
│   │   │   ├── contact.py
│   │   │   ├── contact_change.py
│   │   │   ├── contact_photo.py
│   │   │   ├── lead_event.py
│   │   │   ├── notification.py
│   │   │   ├── offer.py
│   │   │   ├── report.py
│   │   │   ├── review.py
│   │   │   ├── schedule.py
│   │   │   ├── user.py
│   │   │   └── utility_item.py
│   │   ├── repositories/        # Repositorios de datos
│   │   │   ├── __init__.py
│   │   │   ├── contact_repository.py
│   │   │   └── user_repository.py
│   │   ├── routes/              # Rutas API
│   │   │   ├── __init__.py
│   │   │   ├── admin.py
│   │   │   ├── auth.py
│   │   │   ├── categories.py
│   │   │   ├── contacts.py
│   │   │   ├── notifications.py
│   │   │   ├── offers.py
│   │   │   ├── provider.py
│   │   │   ├── reviews.py
│   │   │   └── users.py
│   │   ├── schemas/             # Esquemas Pydantic
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── category.py
│   │   │   ├── contact.py
│   │   │   ├── offer.py
│   │   │   ├── report.py
│   │   │   ├── review.py
│   │   │   ├── user.py
│   │   │   └── utility.py
│   │   └── services/            # Servicios
│   │       ├── __init__.py
│   │       ├── image_service.py
│   │       └── permission_service.py
│   ├── database/
│   │   ├── agenda.db            # Base de datos SQLite
│   │   ├── agenda.db-wal        # WAL journal
│   │   └── agenda.db-shm        # SHM shared memory
│   ├── fuente_datos/
│   │   ├── contactos/          # 190 archivos VCF
│   │   ├── datos_ybarlucea_20km.json
│   │   ├── profesionales_ybarlucea.json
│   │   ├── real_businesses_ybarlucea.json
│   │   ├── consolidated_contacts.json
│   │   ├── import_ybarlucea_data.py
│   │   └── consolidate_and_import.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── integration/
│   │   └── unit/
│   ├── venv/                    # Entorno virtual
│   ├── requirements.txt
│   ├── requirements-test.txt
│   ├── pytest.ini
│   ├── Makefile
│   ├── run.py
│   └── run_debug.py
└── (archivos frontend en la raíz si aplica)
```

---

## Base de Datos

### Tablas Existentes

| Tabla | Registros | Descripción |
|-------|-----------|-------------|
| users | 115 | Usuarios registrados |
| categories | 26 | Categorías de contactos |
| contacts | 451 | Contactos de comercios y servicios |
| contact_history | 5 | Historial de cambios |
| contact_changes | 0 | Cambios pendientes |
| reviews | 1 | Reseñas de contactos |
| offers | 17 | Ofertas |
| lead_events | 1 | Eventos de leads |
| reports | 1 | Reportes |
| utility_items | 0 | Utilidades |
| notifications | 0 | Notificaciones |
| contact_photos | 0 | Fotos de contactos |
| schedules | 14 | Horarios |

### Esquema de `contacts`

| Campo | Tipo | Nullable | Descripción |
|-------|------|----------|-------------|
| id | INTEGER | NO | Primary key |
| name | VARCHAR(100) | NO | Nombre del contacto |
| phone | VARCHAR(20) | NO | Teléfono |
| email | VARCHAR(255) | SI | Correo electrónico |
| address | VARCHAR(255) | SI | Dirección |
| city | VARCHAR(100) | SI | Ciudad |
| neighborhood | VARCHAR(100) | SI | Barrio |
| category_id | INTEGER | SI | FK a categories |
| description | VARCHAR(500) | SI | Descripción |
| user_id | INTEGER | SI | FK a users (creador) |
| schedule | VARCHAR(200) | SI | Horario de atención |
| website | VARCHAR(255) | SI | Sitio web |
| photo_path | VARCHAR(500) | SI | Ruta de foto |
| latitude | FLOAT | SI | Latitud (geo) |
| longitude | FLOAT | SI | Longitud (geo) |
| maps_url | VARCHAR(500) | SI | URL de Google Maps |
| is_verified | BOOLEAN | SI | Verificado (legacy) |
| verified_by | INTEGER | SI | Usuario que verificó |
| verified_at | DATETIME | SI | Fecha de verificación |
| verification_level | INTEGER | SI | Nivel de verificación (0-3) |
| status | VARCHAR(20) | SI | Estado (active, flagged, suspended) |
| avg_rating | REAL | SI | Rating promedio |
| review_count | INTEGER | SI | Cantidad de reseñas |
| pending_changes_count | INTEGER | SI | Cambios pendientes |
| created_at | DATETIME | SI | Fecha de creación |
| updated_at | DATETIME | SI | Fecha de actualización |
| instagram | VARCHAR(100) | SI | Instagram |
| facebook | VARCHAR(255) | SI | Facebook |
| about | TEXT | SI | Acerca de |
| slug | VARCHAR(200) | SI | URL amigable |

### Esquema de `users`

| Campo | Tipo | Nullable | Descripción |
|-------|------|----------|-------------|
| id | INTEGER | NO | Primary key |
| username | VARCHAR(50) | NO | Nombre de usuario |
| email | VARCHAR(255) | NO | Correo electrónico |
| phone_area_code | VARCHAR(10) | NO | Código de área |
| phone_number | VARCHAR(20) | NO | Número de teléfono |
| password_hash | VARCHAR(255) | NO | Hash de contraseña |
| role | VARCHAR(20) | SI | Rol (admin, user, etc.) |
| is_active | BOOLEAN | SI | Usuario activo |
| deactivated_at | DATETIME | SI | Fecha de desactivación |
| deactivated_by | INTEGER | SI | Usuario que desactivó |
| created_at | DATETIME | SI | Fecha de creación |

### Esquema de `categories`

| Campo | Tipo | Nullable | Descripción |
|-------|------|----------|-------------|
| id | INTEGER | NO | Primary key |
| code | INTEGER | NO | Código de categoría |
| name | VARCHAR(100) | NO | Nombre |
| icon | VARCHAR(50) | SI | Ícono |
| description | VARCHAR(255) | SI | Descripción |

---

## API Endpoints

| Método | Ruta | Acceso | Descripción |
|--------|------|--------|-------------|
| GET | `/` | Público | Frontend - Landing |
| GET | `/health` | Público | Health check |
| GET | `/search` | Público | Frontend - Búsqueda |
| GET | `/add` | Público | Frontend - Agregar |
| GET | `/login` | Público | Frontend - Login |
| GET | `/register` | Público | Frontend - Registro |
| POST | `/api/auth/register` | Público | Registro de usuario |
| POST | `/api/auth/login` | Público | Login de usuario |
| GET | `/api/categories` | Público | Listar categorías |
| GET | `/api/contacts` | Público | Listar contactos |
| GET | `/api/contacts/search` | Público | Buscar contactos |
| GET | `/api/contacts/{id}` | Público | Ver contacto |
| POST | `/api/contacts` | Auth | Crear contacto |
| PUT | `/api/contacts/{id}` | Auth | Actualizar contacto |
| DELETE | `/api/contacts/{id}` | Auth | Eliminar contacto |

---

## Modelos de Datos

### Contact (SQLAlchemy)

Ubicación: `backend/app/models/contact.py`

```python
class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255))
    address = Column(String(255))
    city = Column(String(100))
    neighborhood = Column(String(100))
    category_id = Column(Integer, ForeignKey("categories.id"))
    description = Column(String(500))
    user_id = Column(Integer, ForeignKey("users.id"))
    schedule = Column(String(200))
    website = Column(String(255))
    photo_path = Column(String(500))
    latitude = Column(Float)
    longitude = Column(Float)
    maps_url = Column(String(500))
    is_verified = Column(Boolean, default=False)
    verified_by = Column(Integer, ForeignKey("users.id"))
    verified_at = Column(DateTime)
    verification_level = Column(Integer, default=0)
    status = Column(String(20), default="active")
    avg_rating = Column(Float, default=0)
    review_count = Column(Integer, default=0)
    pending_changes_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

---

## Categorías Predefinidas

| Código DB | Código Original | Nombre |
|-----------|-----------------|--------|
| 1 | 100 | Plomero/a |
| 2 | 101 | Gasista |
| 3 | 102 | Electricista |
| 4 | 103 | Peluquería/Barbería |
| 5 | 104 | Albañil |
| 6 | 105 | Pintor |
| 7 | 106 | Carpintero/a |
| 8 | 107 | Supermercado |
| 9 | 108 | Carnicería |
| 10 | 109 | Verdulería |
| 11 | 110 | Panadería |
| 12 | 111 | Tienda de ropa |
| 13 | 112 | Farmacia |
| 14 | 113 | Librería |
| 15 | 114 | Bar |
| 16 | 115 | Restaurant |
| 17 | 116 | Club |
| 18 | 117 | Bazar |
| 19 | 118 | Veterinaria |
| 20 | 119 | Ferretería |
| 21 | 120 | Kiosco |
| 22 | 121 | Juguetería |
| 23 | 122 | Polirrubro |
| 24 | 123 | Cuidado de personas |
| 25 | 124 | Alquiler |
| 26 | 999 | Otro |

---

## Datos de Contactos

### Distribución por Ciudad

| Ciudad | Contactos |
|--------|-----------|
| Ibarlucea | 247 |
| Granadero Baigorria | 22 |
| Rosario | 17 |
| Funes | 17 |
| (otras ciudades) | 148 |

### Distribución por Categoría

| Categoría | Contactos |
|-----------|-----------|
| Otro | 194 |
| Bar | 27 |
| Supermercado | 20 |
| Gasista | 19 |
| Peluquería/Barbería | 15 |
| Ferretería | 14 |
| Electricista | 14 |
| Plomero/a | 14 |
| Veterinaria | 11 |
| Farmacia | 11 |
| Bazar | 11 |
| Albañil | 11 |
| Restaurant | 9 |
| Carnicería | 8 |
| Carpintero/a | 8 |

### Nivel de Verificación

| Nivel | Nombre | Contactos |
|-------|--------|-----------|
| 0 | Sin verificar | 136 |
| 1 | Básico | 216 |
| 2 | Documentado | 70 |
| 3 | Premium | 15 |

---

## Scripts de Importación

### 1. consolidate_and_import.py

**Ubicación**: `backend/fuente_datos/consolidate_and_import.py`

**Funcionalidad**:
- Parsea 190 archivos VCF de la carpeta `contactos`
- Carga datos de archivos JSON:
  - `datos_ybarlucea_20km.json` (83 contactos)
  - `profesionales_ybarlucea.json` (28 contactos)
  - `real_businesses_ybarlucea.json` (37 contactos)
- Filtra por distancia máxima de 20km desde Ybarlucea
- Asigna ciudad por defecto (Ibarlucea) a contactos sin zona
- Detecta categoría por palabras clave del nombre
- Genera JSON consolidado
- Importa a la base de datos

**Coordenadas de Ybarlucea**:
- Latitud: -32.8833
- Longitud: -60.7833

### 2. import_ybarlucea_data.py

**Ubicación**: `backend/fuente_datos/import_ybarlucea_data.py`

**Funcionalidad**:
- Importa datos desde `datos_ybarlucea_20km.json`
- Mapea categorías del sistema viejo al nuevo
- Evita duplicados por nombre + dirección

---

## Configuración Regional

| Configuración | Valor |
|---------------|-------|
| Idioma | Español (Rioplatense) |
| Zona horaria | America/Argentina/Buenos_Aires |
| Moneda | Peso Argentino (ARS) |
| Formato de teléfono | +54 9 XXX XXX XXXX |

---

## Cómo Ejecutar

### Requisitos
- Python 3.12+
- SQLite
- Windows / Linux / macOS

### Pasos

```bash
# 1. Navegar al backend
cd backend

# 2. Activar entorno virtual
# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate

# 3. Ejecutar el servidor
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Abrir en navegador
# http://localhost:8000
```

---

## Historial de Desarrollo

### Metodología
El proyecto sigue el flujo **Spec-Driven Development (SDD)** con las siguientes fases:
1. Explore - Investigar el codebase
2. New - Crear propuesta de cambio
3. Spec - Escribir especificaciones
4. Design - Crear diseño técnico
5. Tasks - Crear checklist de tareas
6. Apply - Implementar código
7. Verify - Verificar implementación
8. Archive - Archivar especificaciones

### Fases Completadas
- ✅ Explore
- ✅ New
- ✅ Spec (SPEC-001, SPEC-002)
- ✅ Design
- ✅ Tasks
- ✅ Apply (Backend + Frontend)
- ✅ Verify
- ✅ Archive

### Importación de Datos (Marzo 2026)

**Proceso de importación de contactos:**

1. **Recolección de datos**:
   - Archivos VCF: 190 contactos
   - JSONs existentes: 148 contactos
   - Total combinado: 338 contactos

2. **Procesamiento**:
   - Filtrados por distancia (20km desde Ybarlucea)
   - Asignación de ciudad por defecto
   - Detección de categoría por palabras clave

3. **Resultados**:
   - Insertados: 186 contactos nuevos
   - Duplicados omitidos: 152
   - Errores: 0

4. **Correcciones aplicadas**:
   - 179 teléfonos malformados corregidos
   - "Ybarlucea" reemplazado por "Ibarlucea"

---

## Notas Importantes

1. **VCF Files**: Los archivos VCF solo contienen nombre y teléfono, sin categoría ni dirección. La categoría se infiere del nombre usando palabras clave.

2. **Coordenadas**: Los contactos VCF tienen coordenadas por defecto del centro de Ybarlucea. Para mejor precisión en el mapa, sería necesario geocodificar las direcciones.

3. **Verificación**: Los contactos importados tienen nivel de verificación 1 (Básico) por defecto.

4. **Autenticación**: El sistema usa JWT para autenticación. Los endpoints de escritura requieren token.

5. **Frontend**: El frontend es completamente estático (HTML + Tailwind CSS + Vanilla JS), comunicarse con la API via fetch().

---

## Archivos Generados/Recientes

| Archivo | Descripción |
|---------|-------------|
| `consolidated_contacts.json` | JSON con todos los contactos combinados |
| `consolidate_and_import.py` | Script principal de importación |
| `get_db_info.py` | Script de verificación de base de datos |

---

*Documento generado automáticamente el 30 de marzo de 2026*
*Proyecto: Agenda Comunitaria - AgendaZonal*
