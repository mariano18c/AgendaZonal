# AgendaZonal - Agent Guide

## Proyecto

- **Nombre**: Agenda de la zona
- **Tipo**: Sistema web completo (FastAPI + SQLite + Tailwind CSS)
- **Plataforma**: Raspberry Pi 5 (4GB RAM)
- **Estado**: ✅ **COMPLETADO** (SPEC-001 a SPEC-004)

## Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Base de datos**: SQLite
- **ORM**: SQLAlchemy
- **Auth**: JWT
- **Testing**: pytest

### Frontend
- **HTML**: Vanilla JS + Templates Jinja2
- **CSS**: Tailwind CSS
- **Mapas**: Leaflet + MarkerCluster
- **PWA**: Service Worker, manifest, push notifications

## Cómo Ejecutar

```bash
# Backend
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (desarrollo)
# El servidor FastAPI sirve archivos estáticos automáticamente en /
# Abrir: http://localhost:8000
```

## Commands Frecuentes

### SDD Workflow
| Comando | Descripción |
|---------|-------------|
| `/sdd-init` | Inicializar contexto SDD |
| `/sdd-explore <topic>` | Investigar código/idea |
| `/sdd-new <change>` | Crear nueva propuesta |
| `/sdd-apply` | Implementar tareas |
| `/sdd-verify` | Verificar implementación |
| `/sdd-archive` | Archivar cambio |

### Git
```bash
# Estado y cambios
git status
git diff

# Commit
git add .
git commit -m "feat: description"

# Push
git push origin main
```

### Testing
```bash
cd backend
pytest tests/ -v
pytest tests/ --cov=app --cov-report=html
```

### Base de Datos
```bash
# Reset completo
rm backend/app.db
cd backend && python -c "from app.database import init_db; init_db()"
```

## Estructura de Proyecto

```
AgendaZonal/
├── backend/
│   ├── app/
│   │   ├── models/      # SQLAlchemy models
│   │   ├── routes/      # FastAPI endpoints
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── services/    # Business logic
│   │   ├── repositories/# Data access
│   │   ├── main.py      # Entry point
│   │   └── database.py  # DB config
│   └── tests/           # Test suite
├── frontend/
│   ├── js/              # Vanilla JS modules
│   ├── *.html           # Pages
│   ├── sw.js            # Service Worker
│   └── manifest.json    # PWA manifest
└── AGENTS.md            # Agent configuration
```
