# Agent Configuration - Agenda Comunitaria

## Proyecto
- **Nombre**: Agenda Comunitaria
- **Tipo**: Sistema web completo (FastAPI + SQLite + Tailwind CSS)
- **Stack**: FastAPI (Python), SQLite, HTML + Tailwind CSS + Vanilla JS
- **Plataforma**: Raspberry Pi 5 (4GB RAM)
- **Estado**: ✅ **COMPLETADO**

## SDD Workflow
Este proyecto sigue el flujo Spec-Driven Development.

### Fases SDD
1. **Explore** → ✅ Completado
2. **New** → ✅ Completado
3. **Spec** → ✅ Completado (SPEC-001, SPEC-002)
4. **Design** → ✅ Completado
5. **Tasks** → ✅ Completado
6. **Apply** → ✅ Completado (Backend + Frontend)
7. **Verify** → ✅ Completado
8. **Archive** → ✅ Completado (SPEC-001, SPEC-002)

### Comandos Disponibles
- `/sdd-explore` - Investigar el codebase
- `/sdd-new` - Crear propuesta de cambio
- `/sdd-apply` - Implementar tareas
- `/sdd-verify` - Verificar implementación
- `/sdd-archive` - Archivar especificaciones

## Estado del Proyecto

### Backend ✅ Completado
- FastAPI configurado con CORS
- SQLite configurado (24 categorías predefinidas)
- Autenticación JWT implementada
- CRUD completo de contactos
- Búsqueda por texto y categoría

### Frontend ✅ Completado
- HTML + Tailwind CSS (CDN) + Vanilla JS
- Responsive (celulares y computadoras)
- 5 páginas: Landing, Search, Add, Login, Register
- Comunicación con API via fetch()

### API Endpoints

| Método | Ruta | Acceso | Estado |
|--------|------|--------|--------|
| GET | `/` | Público | ✅ Frontend |
| GET | `/health` | Público | ✅ |
| GET | `/search` | Público | ✅ Frontend |
| GET | `/add` | Público | ✅ Frontend |
| GET | `/login` | Público | ✅ Frontend |
| GET | `/register` | Público | ✅ Frontend |
| POST | `/api/auth/register` | Público | ✅ |
| POST | `/api/auth/login` | Público | ✅ |
| GET | `/api/categories` | Público | ✅ |
| GET | `/api/contacts` | Público | ✅ |
| GET | `/api/contacts/search` | Público | ✅ |
| GET | `/api/contacts/{id}` | Público | ✅ |
| POST | `/api/contacts` | Auth | ✅ |
| PUT | `/api/contacts/{id}` | Auth | ✅ |
| DELETE | `/api/contacts/{id}` | Auth | ✅ |

### Base de Datos

| Tabla | Campos |
|-------|--------|
| users | id, username, email, phone_area_code, phone_number, password_hash, created_at |
| categories | id, code, name, icon, description |
| contacts | id, name, phone, email, address, city, neighborhood, category_id, description, user_id, created_at, updated_at |

### Categorías Predefinidas (24)
| Código | Nombre |
|--------|--------|
| 100 | Plomero/a |
| 101 | Gasista |
| 102 | Electricista |
| 103 | Peluquería/Barbería |
| 104 | Albañil |
| 105 | Pintor |
| 106 | Carpintero/a |
| 107 | Supermercado |
| 108 | Carnicería |
| 109 | Verdulería |
| 110 | Panadería |
| 111 | Tienda de ropa |
| 112 | Farmacia |
| 113 | Librería |
| 114 | Bar |
| 115 | Restaurant |
| 116 | Club |
| 117 | Bazar |
| 118 | Veterinaria |
| 119 | Ferretería |
| 120 | Kiosco |
| 121 | Juguetería |
| 122 | Polirrubro |
| 999 | Otro |

## Cómo Ejecutar

```bash
cd backend
source venv/bin/activate  # o venv\Scripts\activate en Windows
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Luego abrir: **http://localhost:8000**

## Configuración Regional
- **Idioma**: Español (Español Rioplatense)
- **Zona horaria**: America/Argentina/Buenos_Aires
