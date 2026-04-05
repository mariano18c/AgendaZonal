# AgendaZonal

Directorio hiperlocal de servicios y comercios para barrios de Rosario/Ibarlucea, Argentina.

> Reemplaza revistas publicitarias físicas con una plataforma web PWA con búsqueda geo, reseñas, integración con WhatsApp, y ofertas flash.

---

## Stack

| Componente | Tecnología |
|------------|------------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy, SQLite |
| **Frontend** | HTML5, Tailwind CSS (CDN), Vanilla JS |
| **Mapas** | Leaflet.js + OpenStreetMap |
| **Autenticación** | JWT |
| **Plataforma** | Raspberry Pi 5 (4GB RAM) |

---

## Cómo ejecutar

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Abrir: **http://localhost:8000**

---

## Estructura

```
AgendaZonal/
├── backend/           # FastAPI + SQLite
├── frontend/          # HTML + Tailwind + JS (PWA)
├── SPECS/             # Especificaciones SDD
├── ARCHIVE/           # Especificaciones archivadas
└── TASKS/             # Tareas
```

---

## Estado del Proyecto

| Spec | Descripción | Estado |
|------|-------------|--------|
| SPEC-001 | Autenticación JWT + Cat. predefinidas | ✅ Completado |
| SPEC-002 | CRUD Contactos + Búsqueda | ✅ Completado |
| SPEC-003 | Reseñas + Moderación + Dashboard | ✅ Completado |
| SPEC-004 | Ofertas flash + Photos + Schedules | ✅ Completado |

**Total: 4 specs completados** — Producción

---

## Documentación

- [DOCUMENTACION-COMPLETA.md](./DOCUMENTACION-COMPLETA.md) — Documentación técnica detallada
- [AGENTS.md](./AGENTS.md) — Configuración de agentes y API

---

## Licencia

MIT
