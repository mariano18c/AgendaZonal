# MEMORY.MD - Agenda Zonal

## Decisiones Arquitecturales
- [2026-03-15] Elección de FastAPI sobre Django/Falcon por rendimiento y async nativo
- [2026-03-10] Uso de SQLite para despliegue en Raspberry Pi 5 (limitado a <100 conexiones concurrentes)
- [2026-03-20] Patrón Repository + Service en lugar de Active Record para mejor testabilidad
- [2026-03-25] Implementación de PWA con Workbox para capacidades offline
- [2026-04-01] Uso de Haversine + bounding box para búsquedas geolocalizadas eficientes

## Gotchas y Lecciones Aprendidas
- [2026-03-18] Problema con migraciones Alembic al cambiar tipos de columnas en SQLite (requiere recreación de tabla)
- [2026-03-22] Limitación de FTS5 con caracteres especiales requería sanitización especial (envolver términos en comillas)
- [2026-03-28] Configuración de CORS necesaria para PWA funcionando en dominio diferente al backend
- [2026-04-05] Manejo de estado de autenticación en service workers requiere actualización explícita después del login
- [2026-04-10] Optimización de imágenes requerida para rendimiento en dispositivos móviles

## Patrones Establecidos
- [2026-03-12] Nombre de archivos de ruta: plural (contacts.py, reviews.py)
- [2026-03-14] Sufijo de métodos de servicio: _with_validation para métodos que lanzan excepciones
- [2026-03-16] Convención de eventos: presente simple (contact_created, review_submitted)
- [2026-03-22] Prefijo de pruebas unitarias: test_ seguido de modulo_funcionalidad
- [2026-03-24] Organización de tests por tipo: unit, integration, security, performance

## Configuraciones Específicas del Entorno
- [2026-03-08] Variables de entorno requeridas en producción vs desarrollo
- [2026-03-11] Configuración de uvicorn para producción (workers=2, timeout=30, etc.)
- [2026-03-19] Límites de archivo para upload de fotos (actualmente 5MB)
- [2026-03-26] Configuración de rate limiting (100 requests/hour por IP)
- [2026-04-03] Configuración de VAPID para push notifications