# SPEC-002: CRUD de Contactos

## Metadata
- **Creado**: 2026-03-20
- **Autor**: MarianoC
- **Estado**: active
- **Depende de**: SPEC-001 (Autenticación)

## Overview
Sistema completo de gestión de contactos para la agenda comunitaria.

## Requirements

### Must Have
- [x] Modelo Category con código y nombre
- [x] Modelo Contact con datos completos
- [x] CRUD completo de contactos (Auth requerido para escribir)
- [x] Listado público de contactos
- [x] Búsqueda por nombre, categoría, ciudad, barrio
- [x] Categorías predefinidas (24 categorías)

### Should Have
- [ ] Paginación en listados
- [ ] Ordenamiento por fecha o nombre

### Could Have
- [ ] Filtros avanzados

## User Scenarios

### Scenario 1: Crear contacto
**Given** usuario autenticado
**When** POST `/api/contacts` con datos válidos
**Then** se crea el contacto y se retorna

### Scenario 2: Listar contactos
**Given** cualquier usuario (sin autenticación)
**When** GET `/api/contacts`
**Then** retorna lista de contactos

### Scenario 3: Buscar contactos
**Given** cualquier usuario
**When** GET `/api/contacts/search?q=plomero`
**Then** retorna contactos que coincidan

## Categorías

| Código | Nombre | Icono |
|--------|--------|-------|
| 100 | Plomero/a | wrench |
| 101 | Gasista | fire |
| 102 | Electricista | zap |
| 103 | Peluquería/Barbería | scissors |
| 104 | Albañil | hard-hat |
| 105 | Pintor | paintbrush |
| 106 | Carpintero/a | hammer |
| 107 | Supermercado | shopping-cart |
| 108 | Carnicería | beef |
| 109 | Verdulería | apple |
| 110 | Panadería | bread |
| 111 | Tienda de ropa | shirt |
| 112 | Farmacia | pill |
| 113 | Librería | book |
| 114 | Bar | beer |
| 115 | Restaurant | utensils |
| 116 | Club | music |
| 117 | Bazar | gift |
| 118 | Veterinaria | cat |
| 119 | Ferretería | tool |
| 120 | Kiosco | store |
| 121 | Juguetería | toy |
| 122 | Polirrubro | grid |
| 999 | Otro | more-horizontal |

## Technical Notes
- Category tiene campo `code` para identificación fácil
- Contact tiene FK a Category y User
- Soft delete no implementado (DELETE permanente)
