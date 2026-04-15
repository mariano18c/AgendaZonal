# Proposal: memory-and-agents-enhancement

## Metadata
- **Fecha**: 2026-04-15
- **Autor**: Agent Exploration (based on expert analysis)
- **Estado**: pending_approval
- **Depende de**: SPEC-005 (Merge test coverage) ✅ Completado

## Overview
Proposal to enhance project documentation by adding a MEMORY.MD file to capture architectural decisions, lessons learned, and established patterns, and enhancing AGENTS.md with additional sections for architectural decisions and next steps based on expert analysis from functional, technical, architectural, UI/UX, and IA perspectives.

## Motivation
As the Agenda Zonal project reaches completion status across all SDD phases, there is valuable institutional knowledge that should be preserved for future maintenance and evolution. Expert analysis revealed that while the project is technically sound and functionally complete, there is no systematic way to capture:
- Architectural decisions and tradeoffs made during development
- Lessons learned and gotchas encountered
- Established patterns and conventions
- Contextual information for future developers

Additionally, AGENTS.md, while comprehensive, could benefit from explicit sections documenting key architectural decisions and recommended next steps for future evolution.

## Alcance

### Nuevos archivos a crear
1. **MEMORY.md** - Archivo en la raíz del proyecto para documentar conocimiento institucional

### Mejoras a archivos existentes
1. **AGENTS.md** - Adición de secciones para:
   - Decisiones Arquitecturales Clave
   - Próximos Pasos Recomendados
   - Límites de Escalabilidad Conocidos

## Detalles de Implementación

### MEMORY.md Estructura Propuesta
```markdown
# MEMORY.MD - Agenda Zonal

## Decisiones Arquitecturales
- [Fecha] Elección de FastAPI sobre Django/Falcon por rendimiento y async nativo
- [Fecha] Uso de SQLite para despliegue en Raspberry Pi 5 (limitado a <100 conexiones concurrentes)
- [Fecha] Patrón Repository + Service en lugar de Active Record para mejor testabilidad
- [Fecha] Implementación de PWA con Workbox para capacidades offline
- [Fecha] Uso de Haversine + bounding box para búsquedas geolocalizadas eficientes

## Gotchas y Lecciones Aprendidas
- [Fecha] Problema con migraciones Alembic al cambiar tipos de columnas en SQLite (requiere recreación de tabla)
- [Fecha] Limitación de FTS5 con caracteres especiales requería sanitización especial (envolver términos en comillas)
- [Fecha] Configuración de CORS necesaria para PWA funcionando en dominio diferente al backend
- [Fecha] Manejo de estado de autenticación en service workers requiere actualización explícita después del login
- [Fecha] Optimización de imágenes requerida para rendimiento en dispositivos móviles

## Patrones Establecidos
- [Fecha] Nombre de archivos de ruta: plural (contacts.py, reviews.py)
- [Fecha] Sufijo de métodos de servicio: _with_validation para métodos que lanzan excepciones
- [Fecha] Convención de eventos: presente simple (contact_created, review_submitted)
- [Fecha] Prefijo de pruebas unitarias: test_ seguido de modulo_funcionalidad
- [Fecha] Organización de tests por tipo: unit, integration, security, performance

## Configuraciones Específicas del Entorno
- [Fecha] Variables de entorno requeridas en producción vs desarrollo
- [Fecha] Configuración de uvicorn para producción (workers=2, timeout=30, etc.)
- [Fecha] Límites de archivo para upload de fotos (actualmente 5MB)
- [Fecha] Configuración de rate limiting (100 requests/hour por IP)
- [Fecha] Configuración de VAPID para push notifications
```

### AGENTS.md Mejoras Propuestas
Agregar las siguientes secciones al final del archivo:

#### Decisiones Arquitecturales Clave
Resumen de las decisiones técnicas más importantes tomadas durante el desarrollo del proyecto, incluyendo tradeoffs considerados y razones detrás de cada elección.

#### Próximos Pasos Recomendados
Basado en el análisis de expertos, recomendaciones para futuras evoluciones del proyecto, incluyendo:
- Oportunidades de integración de IA identificadas
- Mejoras de experiencia de usuario
- Escalabilidad y rendimiento
- Seguridad y monitoreo

#### Límites de Escalabilidad Conocidos
Documentación de los límites actuales del sistema y cuándo considerar migraciones tecnológicas:
- Límite de conexiones concurrentes de SQLite
- Consideraciones para migrar a PostgreSQL/MySQL
- Estrategias de caching para mejorar rendimiento
- Consideraciones de despliegue en múltiples instancias

## Beneficios
- Preservación del conocimiento institucional para mantenimiento futuro
- Mejora del onboarding de nuevos desarrolladores al proyecto
- Documentación explícita de tradeoffs técnicos tomados
- Guía para futuras evoluciones basadas en análisis de expertos
- Reducción del riesgo de perder conocimiento crítico del proyecto

## Próximos Pasos
1. Crear el archivo MEMORY.md con la estructura propuesta
2. Mejorar AGENTS.md con las secciones adicionales recomendadas
3. Revisar y validar las adiciones con el equipo de desarrollo
4. Considerar estas mejoras como parte del cierre del ciclo SDD actual

---
**¿Procedo con la creación del SPEC detallado para esta propuesta?**