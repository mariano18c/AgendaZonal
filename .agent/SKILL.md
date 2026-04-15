# Project Skills - AgendaZonal

## Frequent Commands

### Development
```bash
# Start server
cd backend && uvicorn app.main:app --reload

# Run tests
cd backend && pytest -v

# Create migration
cd backend && alembic revision --autogenerate -m "description"

# Reset database
rm backend/app.db && cd backend && python -c "from app.database import init_db; init_db()"
```

### Git
```bash
# Check status
git status

# Add and commit
git add -A && git commit -m "feat: description"

# Push
git push origin main
```

## Technical FAQs

### Q: ¿Cómo agregar un nuevo endpoint?
1. Crear función en `routes/{recurso}.py`
2. Usar decorators `@router.get/ post/ put/ delete`
3. Definir schemas en `schemas/{recurso}.py`
4. Agregar a `main.py` con `app.include_router`

### Q: ¿Cómo agregar un nuevo campo a un modelo?
1. Agregar columna en `models/{modelo}.py`
2. Agregar campo en schema对应 `schemas/{modelo}.py`
3. Crear migración: `alembic revision --autogenerate -m "add field"`
4. Aplicar migración: `alembic upgrade head`

### Q: ¿Cómo agregar un nuevo test?
1. Crear archivo en `tests/`
2. Usar fixtures de `conftest.py`
3. Nombrar test como `test_{modulo}_{funcionalidad}`
4. Ejecutar: `pytest tests/{archivo}.py -v`

### Q: ¿Cómo modificar el diseño (Tailwind)?
1. Editar `frontend/tailwind.config.js`
2. Ejecutar `npm run build` para regenerar CSS
3. O usar Tailwind CDN para desarrollo rápido

### Q: ¿Cómo hacer debug de errores?
1. Revisar logs del servidor (uvicorn output)
2. Usar `print()` para debugging rápido
3. Revisar browser console (F12)
4. Revisar network tab para requests fallidos

## Implementation Patterns

### Pattern: Adding a New API Endpoint

```python
# 1. Define schema (schemas/contact.py)
class MyObjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class MyObjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]

# 2. Create route (routes/myresource.py)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/myresource", tags=["myresource"])

@router.post("/", response_model=MyObjectResponse)
def create_myobject(
    obj: MyObjectCreate,
    db: Session = Depends(get_db)
):
    # Business logic here
    return db_obj

# 3. Register in main.py
from app.routes import myresource
app.include_router(myresource.router)
```

### Pattern: Frontend API Call

```javascript
// api.js
async function createMyObject(data) {
  const response = await fetch('/api/myresource/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getToken()}`
    },
    body: JSON.stringify(data)
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Error creating object');
  }
  
  return response.json();
}
```

### Pattern: Form Submission Handler

```javascript
async function handleSubmit(event) {
  event.preventDefault();
  
  const submitBtn = event.target.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Guardando...';
  
  try {
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData);
    
    await createMyObject(data);
    
    showSuccess('Creado exitosamente');
    window.location.href = '/list';
  } catch (error) {
    showError(error.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Guardar';
  }
}
```

### Pattern: Repository Pattern

```python
# repositories/contact_repository.py
class ContactRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, contact_id: int) -> Optional[Contact]:
        return self.db.query(Contact).filter(Contact.id == contact_id).first()
    
    def search(self, query: str, category: Optional[int] = None):
        stmt = self.db.query(Contact).filter(Contact.name.ilike(f"%{query}%"))
        if category:
            stmt = stmt.filter(Contact.category_id == category)
        return stmt.all()
```

### Pattern: Service Layer

```python
# services/contact_service.py
class ContactService:
    def __init__(self, repository: ContactRepository):
        self.repository = repository
    
    def get_contact_with_validation(self, contact_id: int) -> Contact:
        contact = self.repository.get_by_id(contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contacto no encontrado")
        return contact
```

### Pattern: Handling Auth in Routes

```python
# Using dependency
from app.auth import get_current_user

@router.post("/contacts")
def create_contact(
    contact: ContactCreate,
    current_user: User = Depends(get_current_user)
):
    # current_user.id is available
    # Only authenticated users can access
    return {"id": 1, "owner_id": current_user.id}
```

### Pattern: Form with Validation

```html
<form id="myForm" onsubmit="handleSubmit(event)">
  <div class="mb-4">
    <label class="block text-gray-700 text-sm font-bold mb-2" for="name">
      Nombre
    </label>
    <input 
      class="w-full border border-gray-300 rounded px-3 py-2"
      id="name" 
      name="name" 
      required 
      minlength="3"
      maxlength="100"
    >
  </div>
  <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded">
    Guardar
  </button>
</form>
```

### Pattern: Loading State with Spinner

```javascript
function showLoading() {
  return `
    <div class="flex justify-center items-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>
  `;
}

function renderContacts(contacts) {
  if (loading) return showLoading();
  if (contacts.length === 0) return renderEmpty();
  return contacts.map(c => renderCard(c)).join('');
}
```

### Pattern: Map with Markers

```javascript
function initMap() {
  const map = L.map('map').setView([-33.0, -68.8], 13);
  
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
  }).addTo(map);
  
  return map;
}

function addMarkers(map, contacts) {
  contacts.forEach(contact => {
    if (contact.latitude && contact.longitude) {
      L.marker([contact.latitude, contact.longitude])
        .addTo(map)
        .bindPopup(`<b>${contact.name}</b><br>${contact.address}`);
    }
  });
}
```

### Pattern: JWT Token Handling

```javascript
// Get token from localStorage
function getToken() {
  return localStorage.getItem('token');
}

// Set token after login
function setToken(token) {
  localStorage.setItem('token', token);
}

// Remove token on logout
function clearToken() {
  localStorage.removeItem('token');
}

// Include in API calls
function apiCall(url, options = {}) {
  const token = getToken();
  if (token) {
    options.headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    };
  }
  return fetch(url, options);
}
```

## Error Messages (Spanish Rioplatense)

### Common Error Messages
- "Usuario o contraseña incorrectos"
- "El correo electrónico ya está registrado"
- "El nombre de usuario ya está en uso"
- "El contacto no fue encontrado"
- "No tienes permisos para realizar esta acción"
- "Debes iniciar sesión para continuar"
- "El formato del correo electrónico no es válido"
- "La contraseña debe tener al menos 8 caracteres"
- "El campo es obligatorio"
- "Error al conectar con el servidor"
