# Convenciones de Desarrollo y Patrones: High-Efficiency

Este documento detalla los estándares técnicos para garantizar la mantenibilidad y el rendimiento en el hardware objetivo (Raspberry Pi 5).

## Backend Architecture (FastAPI + SQLAlchemy)

### 1. Repository Pattern (Strict)
Los Repositorios son los únicos autorizados para interactuar con `db.query`.
- **Ubicación**: `backend/app/repositories/`
- **Regla**: No se debe retornar el objeto `query`, sino siempre el resultado ejecutado (`.first()`, `.all()`, `.scalar()`).

### 2. Service Layer (Business Logic)
Los servicios orquestan repositorios y lanzan excepciones de FastAPI.
- **Ubicación**: `backend/app/services/`
- **Naming**: Los métodos que pueden fallar por "no encontrado" deben usar el sufijo `_with_validation`.

### 3. Schemas (Pydantic v2)
Uso de validación estricta para prevenir inyección de datos basura.
```python
class ContactBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
    name: str = Field(..., min_length=3, max_length=100)
```

---

## Performance Patterns for RPi 5

### I/O Management
- **Async Everywhere**: Todos los endpoints de la API deben ser `async def` para no bloquear el Event Loop de Uvicorn.
- **No Heavy Loops**: Cualquier procesamiento pesado de listas (>1000 items) debe hacerse mediante generadores o paginación en base de datos.
- **Logging**: Usar `logging.handlers.RotatingFileHandler` para no saturar el espacio en la SD.

---

## Global Error Handling Pattern

No usar `try/except` genéricos en las rutas. Usar el handler global definido en `main.py` y lanzar excepciones específicas:
```python
raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail={"msg": "Stock insuficiente para oferta flash", "code": "ERR_STOCK_LOW"}
)
```

---

---

## Data Integrity & Normalization

Para garantizar la consistencia en el motor de búsqueda y el sistema de mensajería (WhatsApp):

1. **Standard Phone Format**: Todos los números deben almacenarse en formato internacional estricto: `+549` + área (sin 0) + número (sin 15). Ejemplo: `+5493412691071`.
2. **VCF Parsing Logic**: 
   - Usar Regex *non-greedy* para capturar campos (ej: `TEL.*:(.*?)`).
   - Soportar parámetros de metadatos (ej: `waid=...`).
   - Fallback: Si el campo `TEL` es inválido, intentar extraer el número del campo `FN` (Full Name).
3. **Duplicate Management**:
   - **Cross-status**: Antes de ingerir un contacto `pending`, verificar si ya existe filtrando por el teléfono normalizado.
   - **Internal**: Periódicamente limpiar la cola de moderación (`pending`) manteniendo solo el registro con "mejor" información (priorizando aquellos con referencia a archivos VCF/Imagen).
4. **Validation (Pydantic)**:
   - Los esquemas de actualización deben permitir el signo `+`.
   - `min_length` para teléfonos debe ser bajo (ej: 3) para permitir números cortos de emergencia (144, 911).

5. **Logging Dedicado**: Deben escribir en sus propios archivos en `backend/logs/` usando `UTF-8` para compatibilidad multiplataforma.
6. **Debounce Pattern**: Al monitorear archivos, esperar un tiempo prudencial (ej: 3s) para asegurar que el archivo terminó de escribirse.
7. **Resiliencia**: Los daemons deben capturar excepciones globales para no morir ante un archivo corrupto, registrando el error y continuando con el siguiente archivo.

---

## Background Services (Daemons & Watchers)

## Frontend Architecture (Vanilla JS Modular)


### Module Pattern
Cada página tiene su propio archivo JS que exporta una función `init()`.
- **Evitar Polución Global**: No declarar variables en `window` a menos que sea estrictamente necesario (ej: `API_BASE_URL`).
- **State Management**: Usar el patrón Observer simple para cambios que afecten a múltiples componentes UI.

---

## Git & Workflow
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `perf:`.
- **PRs**: Cada cambio debe pasar el linter (`flake8`) y los tests unitarios antes de ser mergeado.

