# Proposal: crud-contactos

## Metadata
- **Fecha**: 2026-03-20
- **Autor**: MarianoC
- **Estado**: pending_approval
- **Depende de**: SPEC-001 (Autenticación) ✅ Completado

## Overview
Sistema completo de gestión de contactos para la agenda comunitaria. Permite a usuarios autenticados crear, leer, actualizar y eliminar contactos de proveedores de servicios y comercios.

## Motivation
La funcionalidad core de la agenda comunitaria es poder registrar y buscar proveedores de servicios. Sin CRUD de contactos, no hay agenda.

## Alcance

### Modelos a crear

**Category**
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code INTEGER UNIQUE NOT NULL,
    name TEXT UNIQUE NOT NULL,
    icon TEXT,
    description TEXT
);
```

**Contact**
```sql
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    address TEXT,
    city TEXT,
    neighborhood TEXT,
    category_id INTEGER,
    description TEXT,
    user_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Endpoints

| Método | Ruta | Acceso | Descripción |
|--------|------|--------|-------------|
| GET | `/api/categories` | Público | Listar categorías |
| GET | `/api/contacts` | Público | Listar contactos |
| GET | `/api/contacts/{id}` | Público | Detalle de contacto |
| GET | `/api/contacts/search?q=...` | Público | Buscar contactos |
| POST | `/api/contacts` | Auth | Crear contacto |
| PUT | `/api/contacts/{id}` | Auth | Editar contacto |
| DELETE | `/api/contacts/{id}` | Auth | Eliminar contacto |

### Categorías iniciales

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

## Beneficios
- Registro público de proveedores de servicios
- Búsqueda fácil por categoría y ubicación
- Accesible desde cualquier dispositivo
- Sin necesidad de apps externas

---

**¿Procedo con la creación del SPEC-002 detallado?**