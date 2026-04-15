# Code Conventions - AgendaZonal

## Python Conventions

### Naming
- **Classes**: `PascalCase` (e.g., `User`, `ContactRepository`)
- **Functions/methods**: `snake_case` (e.g., `get_user_by_id`, `create_contact`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_PHOTOS`, `DEFAULT_CITY`)
- **Private methods**: `_single_underscore_prefix` (e.g., `_validate_email`)
- **Database tables**: `snake_case` (e.g., `users`, `contact_photos`)

### File Structure
```
app/
├── models/           # SQLAlchemy models (one class per file)
├── routes/           # FastAPI routers (one resource per file)
├── schemas/          # Pydantic schemas (request/response)
├── services/         # Business logic (one service per file)
└── repositories/     # Data access (one repository per file)
```

### Import Order
```python
# 1. Standard library
from datetime import datetime
from typing import Optional

# 2. Third party
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

# 3. Local application
from app.database import Base
from app.models.user import User
from app.schemas.user import UserResponse
```

### Route Organization
- CRUD routes en archivos dedicados por recurso (`contacts.py`, `users.py`)
- Prefijos de ruta reflejan estructura de URL (`/api/contacts`)
- Tags en decorators para OpenAPI (`@router.get("/", tags=["contacts"])`)

### Error Handling
- Usar `HTTPException` de FastAPI para errores HTTP
- Códigos: 400 (bad request), 401 (unauthorized), 403 (forbidden), 404 (not found), 500 (server error)
- Mensajes claros en español rioplatense

## JavaScript Conventions

### Naming
- **Functions**: `camelCase` (e.g., `loadContacts`, `renderCard`)
- **Classes**: `PascalCase` (e.g., `ContactForm`, `MapManager`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `API_BASE_URL`)
- **Private functions**: `_single_underscore_prefix`

### File Structure
```
frontend/js/
├── api.js           # API calls
├── app.js           # Main app logic
├── geo.js           # Map/geo logic
└── contact-form.js  # Contact form logic
```

### DOM Manipulation
- Usar `document.getElementById()` para selección por ID
- Usar `classList.add/remove/toggle` para estados
- Evitar `innerHTML` para prevenir XSS — usar `textContent` o `createElement`

### Event Handling
- Usar `addEventListener` en lugar de inline handlers
- Delegar eventos cuando hay múltiples elementos similares
- Siempre hacer cleanup de event listeners en cleanup functions

### Async/Await
- Siempre usar try/catch para manejo de errores
- Mostrar feedback al usuario (loading states, error messages)
- Usar AbortController para cancelar requests si es necesario

## SQL Conventions

### Table Names
- `snake_case` en plural: `users`, `contacts`, `reviews`
- Nombres descriptivos: `contact_photos` (no `photos`)

### Column Names
- `snake_case`: `phone_number`, `created_at`, `verification_level`
- Prefijos de Foreign Key: `user_id`, `contact_id`

### Queries
- Usar parameterized queries para prevenir SQL injection
- Prefijos de tabla en columnas ambiguas: `contacts.name`
- Usar alias para joins: `SELECT c.id, c.name FROM contacts c`

## Git Conventions

### Commit Messages
```
feat: agregar búsqueda por categoría
fix: corregir validación de teléfono
docs: actualizar README
test: agregar tests de autenticación
refactor: separar lógica de contacto en repository
```

### Branch Naming
- `feature/nombre` - nueva funcionalidad
- `fix/nombre` - corrección de bug
- `hotfix/nombre` - corrección urgente

## API Response Conventions

### JSON Structure
```json
{
  "data": { ... },
  "message": "Mensaje opcional",
  "pagination": { "page": 1, "total": 100 }
}
```

### Error Response
```json
{
  "detail": "Mensaje de error claro"
}
```

### Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limited
- `500` - Internal Server Error
