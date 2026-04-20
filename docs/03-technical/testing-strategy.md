# Testing Strategy

## Overview

Este documento describe la estrategia de testing del proyecto AgendaZonal, incluyendo tipos de tests, cobertura mínima y configuración CI/CD.

## Test Structure

```
backend/
├── tests/
│   ├── unit/              # Tests unitarios
│   │   ├── test_models.py
│   │   ├── test_schemas.py
│   │   ├── test_geo.py
│   │   ├── test_captcha.py
│   │   └── test_services.py
│   ├── integration/       # Tests de integración
│   │   ├── test_contacts.py
│   │   ├── test_reviews.py
│   │   ├── test_auth.py
│   │   ├── test_search.py
│   │   ├── test_geo.py
│   │   └── test_notifications.py
│   └── security/        # Tests de seguridad
│       ├── test_sql_injection.py
│       ├── test_jwt.py
│       ├── test_fuzzing.py
│       ├── test_race_conditions.py
│       └── test_access_control.py
```

## Test Types

### Unit Tests
- **Objetivo**: Probar unidades individuales de código
- **Scope**: Models, schemas, funciones utilitarias, lógica de negocio aislada
- **DB**: No usa base de datos real (mock o in-memory)
- **Ejecución**: `pytest backend/tests/unit/ -v`

### Integration Tests
- **Objetivo**: Probar interacción entre componentes
- **Scope**: API endpoints, base de datos, servicios externos
- **DB**: SQLite en memoria (test database)
- **Ejecución**: `pytest backend/tests/integration/ -v`
- **Cleanup**: Rollback automático después de cada test

### Security Tests
- **Objetivo**: Verificar seguridad de la aplicación
- **Scope**: SQL injection, JWT validation, access control
- **Herramientas**: Fuzzing, property-based testing
- **Ejecución**: `pytest backend/tests/security/ -v`

## Coverage Targets

| Type | Target mínimo |
|------|-----------|
| Unit | ≥ 90% |
| Integration | ≥ 80% |
| Overall | ≥ 85% |

## Running Tests

### Local
```bash
# Todos los tests
pytest backend/tests/ -v --cov=app --cov-report=html

# Solo unitarios
pytest backend/tests/unit/ -v

# Solo integración
pytest backend/tests/integration/ -v

# Con coverage
pytest backend/tests/ --cov=app --cov-report=term-missing
```

### CI/CD (GitHub Actions)

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest backend/tests/ -v --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
```

## Fixtures

### Database Fixture
```python
@pytest.fixture
def test_db():
    """Crea base de datos en memoria para tests."""
    from app.database import Base
    from sqlalchemy import create_engine
    
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    yield engine
    
    engine.dispose()
```

### Auth Fixture
```python
@pytest.fixture
def auth_headers(test_db):
    """Headers con token JWT válido."""
    token = create_test_token(user_id=1, role="admin")
    return {"Authorization": f"Bearer {token}"}
```

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Tests lentos | Usar `pytest-xdist` para paralelo: `pytest -n auto` |
| DB lock | Asegurar SQLite WAL mode en test config |
| Flaky tests | Usar `pytest-rerunfailures` |