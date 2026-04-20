# Changelog: AgendaZonal

## [1.2.0] - 2026-04-20
### Added
- **AI-INTERACTION.md**: Nueva guía de estrategia para asistentes IA y plantillas de prompts.
- **Roadmap.md**: Planificación estratégica para 2026-2027.
- **Environment.md**: Documentación completa de configuración de entorno.
- **ADR 005**: Documentación de la decisión técnica de pre-filtrado geoespacial.

### Changed
- **Documentation Overhaul**: Sincronización completa de `/docs` con la realidad del código (`backend/app/...`).
- **Database Schema**: Actualizado para reflejar las 14 tablas del sistema actual.
- **API Catalog**: Redefinición completa de endpoints de moderación, búsqueda y administración.
- **Design System**: Migración a estética "Premium" con tokens HSL y glassmorphism.

### Fixed
- Inconsistencias de rutas en `directory-structure.md`.
- Ubicación de documentos de seguridad desplazados a `05-operations/security`.

---

## [1.1.0] - 2026-04-10
### Added
- **Web Push**: Sistema de notificaciones VAPID para ofertas flash.
- **Moderation Buffer**: Implementación de `contact_changes` para edición colaborativa.
- **Geo Search**: Lógica personalizada de Haversine + Bounding Box.

---

## [1.0.0] - 2026-03-15
### Added
- **Base Project**: Backend FastAPI y Frontend Vanilla JS inicial.
- **Auth**: JWT via HttpOnly cookies.
- **PWA**: Service Worker básico y manifiesto.
- **Deployment**: Configuración inicial de Caddy para Raspberry Pi 5.
