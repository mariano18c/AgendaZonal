# ARCHIVE-006: Documentation Refactor & Root Cleanup

## Fecha
2026-04-20

## Resumen
Se realizó una reestructuración masiva del sistema de conocimiento del proyecto para eliminar la fragmentación y la redundancia, estableciendo una **Única Fuente de Verdad** en el directorio `/docs`.

## Acciones Realizadas
1.  **Migración de Core Docs**: `AGENTS.md`, `MEMORY.md`, `DOCUMENTACION-COMPLETA.md` y `ANALISIS-ESTADO-PROYECTO.md` fueron absorbidos por la estructura modular de `/docs`.
2.  **Consolidación Técnica**: La carpeta `.agent/` fue migrada a `docs/02-architecture/conventions.md` y `design-system.md`.
3.  **Context Routing**: Se reescribió `.cursorrules` para funcionar como un router inteligente de contexto, forzando la lectura de guías específicas según el scope de trabajo.
4.  **Root Sanitization**: Se limpió la raíz del proyecto, dejando solo los directorios operativos (`backend/`, `frontend/`, `docs/`) y archivos de configuración esenciales.
5.  **SDD Lifecycle Migration**: Las carpetas `SPECS`, `ARCHIVE`, `TASKS`, `sdd` y `openspec` fueron movidas a `docs/00-context/sdd-lifecycle/` para preservar el historial sin contaminar el root.

## Resultado Final
Un entorno de desarrollo más predecible para IAs y humanos, con menor carga cognitiva y mayor precisión en la recuperación de contexto técnico.
