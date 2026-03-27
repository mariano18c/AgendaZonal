# SDD - Spec-Driven Development

## Proyecto
- **Nombre**: Agenda Comunitaria
- **Fecha de inicio**: 2026-03-20
- **Estado**: COMPLETADO (Backend + Frontend funcionando)
- **Stack**: FastAPI + SQLite + Tailwind CSS
- **Plataforma**: Raspberry Pi 5 (4GB RAM)

## Fases SDD

| Fase | Estado | Descripción |
|------|--------|-------------|
| Explore | ✅ Completado | Investigar codebase existente |
| New | ✅ Completado | Crear propuesta de cambio |
| Spec | ✅ Completado (SPEC-001, SPEC-002) | Escribir especificaciones |
| Design | ✅ Completado | Diseño técnico |
| Tasks | ✅ Completado | Descomponer en tareas |
| Apply | ✅ Completado (Backend + Frontend) | Implementar |
| Verify | ✅ Completado | Verificar contra specs |
| Archive | ✅ Completado (SPEC-001, SPEC-002) | Archivar specs completadas |

## Estructura de Archivos

```
AgendaZonal/
├── AGENTS.md              # Configuración del agente
├── SDD.md                 # Este documento
├── ARCHIVE/               # Archivos archivados
│   ├── ARCHIVE-001-autenticacion.md
│   ├── ARCHIVE-002-crud-contactos.md
│   ├── PROPOSAL-002-crud-contactos.md
│   └── SPEC-002-crud-contactos.md
├── SPECS/                 # Especificaciones
│   ├── SPEC-001-template.md
│   ├── SPEC-002-crud-contactos.md
│   ├── EXPLORE-001-initial.md
│   ├── PROPOSAL-001-setup-proyecto-base.md
│   └── PROPOSAL-002-crud-contactos.md
├── TASKS/                 # Tareas
│   └── TASK-001-template.md
├── backend/               # Backend (FastAPI)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py        # FastAPI app + frontend static files
│   │   ├── config.py      # Configuración
│   │   ├── database.py    # SQLite connection
│   │   ├── auth.py        # JWT utilities
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py    # User model
│   │   │   ├── category.py # Category model
│   │   │   └── contact.py # Contact model
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py    # Auth endpoints
│   │   │   ├── categories.py # Category endpoints
│   │   │   └── contacts.py # Contact CRUD
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── auth.py    # Auth schemas
│   │       ├── category.py # Category schemas
│   │       └── contact.py # Contact schemas
│   ├── requirements.txt
│   ├── init_db.py         # Initialize DB with categories
│   ├── venv/
│   └── database/
│       └── agenda.db      # SQLite database
└── frontend/              # Frontend (HTML + Tailwind + JS)
    ├── index.html         # Landing page
    ├── search.html        # Search page
    ├── add.html           # Add contact (requires login)
    ├── login.html         # Login
    ├── register.html      # Register
    ├── css/
    └── js/
        ├── api.js         # API communication
        └── app.js         # Main logic
```

## Especificaciones

| Spec | Nombre | Estado | Archivado |
|------|--------|--------|-----------|
| SPEC-001 | Autenticación de usuarios | ✅ Completado | ✅ ARCHIVE-001 |
| SPEC-002 | CRUD de contactos | ✅ Completado | ✅ ARCHIVE-002 |
| SPEC-003 | Sistema de búsqueda | ✅ Implementado | No |
| SPEC-004 | Comentarios | ⏳ Pendiente | No |

## API Endpoints (Implementados)

| Método | Ruta | Acceso | Estado |
|--------|------|--------|--------|
| GET | `/` | Público | ✅ (Frontend) |
| GET | `/health` | Público | ✅ |
| GET | `/search` | Público | ✅ (Frontend) |
| GET | `/add` | Público | ✅ (Frontend) |
| GET | `/login` | Público | ✅ (Frontend) |
| GET | `/register` | Público | ✅ (Frontend) |
| POST | `/api/auth/register` | Público | ✅ |
| POST | `/api/auth/login` | Público | ✅ |
| GET | `/api/categories` | Público | ✅ |
| GET | `/api/contacts` | Público | ✅ |
| GET | `/api/contacts/search` | Público | ✅ |
| GET | `/api/contacts/{id}` | Público | ✅ |
| POST | `/api/contacts` | Auth | ✅ |
| PUT | `/api/contacts/{id}` | Auth | ✅ |
| DELETE | `/api/contacts/{id}` | Auth | ✅ |

## Base de Datos

### Tablas
- **users**: username, email, phone_area_code, phone_number, password_hash
- **categories**: code, name, icon, description (24 categorías predefinidas)
- **contacts**: name, phone, email, address, city, neighborhood, category_id, description, user_id

### Categorías Predefinidas (24)
Plomero/a (100), Gasista (101), Electricista (102), Peluquería/Barbería (103), Albañil (104), Pintor (105), Carpintero/a (106), Supermercado (107), Carnicería (108), Verdulería (109), Panadería (110), Tienda de ropa (111), Farmacia (112), Librería (113), Bar (114), Restaurant (115), Club (116), Bazar (117), Veterinaria (118), Ferretería (119), Kiosco (120), Juguetería (121), Polirrubro (122), Otro (999)

## Frontend

| Página | URL | Descripción |
|--------|-----|-------------|
| Landing | `/` | Categorías + últimos contactos + búsqueda |
| Search | `/search` | Búsqueda por texto + filtro por categoría |
| Add | `/add` | Formulario para agregar contacto (requiere login) |
| Login | `/login` | Iniciar sesión |
| Register | `/register` | Crear cuenta |

## Cómo Ejecutar

```bash
cd backend
source venv/bin/activate  # o venv\Scripts\activate en Windows
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Luego abrir: **http://localhost:8000**

## Registro de Actividad

### 2026-03-20
- INIT: Proyecto inicializado con SDD
- EXPLORE: Análisis de proyecto vacío completado
- NEW: Propuesta setup-proyecto-base creada
- SPEC: SPEC-001 (Autenticación) aprobado
- DESIGN: Arquitectura backend definida (FastAPI + SQLite + JWT)
- TASKS: 7 tareas descompuestas de SPEC-001
- APPLY: TASK-001 a 007 completadas
- VERIFY: Testing manual completado
- ARCHIVE: SPEC-001 archivado

### 2026-03-23
- SPEC: SPEC-002 (CRUD de contactos) aprobado
- APPLY: Modelos Category y Contact implementados
- APPLY: Endpoints CRUD completos (GET, POST, PUT, DELETE)
- APPLY: 24 categorías predefinidas inicializadas
- VERIFY: Todos los endpoints funcionando
- ARCHIVE: SPEC-002 archivado
- APPLY: Frontend completo (5 páginas HTML + Tailwind CSS + JS)
- VERIFY: Frontend funcional con búsqueda, categorías, login/registro
- STATUS: **PROYECTO COMPLETADO**
