# 📍 AgendaZonal — Directorio Hiperlocal

Directorio digital de servicios y comercios para barrios de Rosario e Ibarlucea, Argentina. Una solución moderna (PWA) para conectar vecinos con proveedores de confianza, optimizada para funcionar en **Raspberry Pi 5**.

---

## 🚀 Guía de Inicio Rápido

### Requisitos
- Python 3.11+
- Virtualenv

### Instalación
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate | Linux: source venv/bin/activate

pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Acceder: `http://localhost:8000`

---

## 📚 Documentación Técnica (SSOT)

Toda la documentación técnica, decisiones de arquitectura y guías de desarrollo se han centralizado en el directorio `/docs`.

| Sección | Descripción |
|---------|-------------|
| [**Contexto**](./docs/00-context/project-brief.md) | Visión, Stack y Límites de Hardware. |
| [**Arquitectura**](./docs/02-architecture/conventions.md) | Patrones de código, convenciones y ADRs. |
| [**Diseño**](./docs/02-architecture/design-system.md) | Sistema de diseño, Tailwind y UX Patterns. |
| [**Técnico**](./docs/03-technical/database-schema.md) | Esquema de DB y catálogo de API Endpoints. |
| [**Operaciones**](./docs/05-operations/deployment-rpi5.md) | Despliegue en RPi 5 y configuración de Caddy. |

---

## 🏗️ Estructura del Proyecto

- `backend/`: FastAPI App, Repositorios, Servicios y Modelos.
- `frontend/`: Páginas HTML, Service Worker y Logic JS (PWA).
- `docs/`: **Única fuente de verdad** para documentación técnica.
- `SPECS/`: Especificaciones SDD (Spec-Driven Development) archivadas.

---

## ⚖️ Licencia
Este proyecto está bajo la licencia [MIT](./LICENSE).
