/docs
│
├── 00-context/                 ← Identidad y Contexto Maestro
│   ├── AI-MASTER-PROMPT.md     ← Perfil del Agente
│   ├── AI-INTERACTION.md       ← Estrategia IA y Templates de Prompts
│   ├── project-brief.md        ← Visión, Stack y Límites RPi 5
│   └── sdd-lifecycle/          ← Historial SDD (SPECS, ARCHIVE, TASKS)
│
├── 01-product/                 ← Estrategia y Requerimientos
│   ├── vision-y-negocio.md     ← Visión, SWOT y Monetización
│   ├── user-stories.md         ← Historias de Usuario (Admin/User)
│   └── roadmap.md              ← Planificación Q2 2026 - Q1 2027
│
├── 02-architecture/            ← Decisiones y Estándares
│   ├── design-system.md        ← UIX Premium, Tailwind y PWA Patterns
│   ├── conventions.md          ← Patterns (backend/app/...) y Clean Code
│   └── adr/                    ← Architecture Decision Records
│       ├── 001-sqlite-over-pg.md
│       ├── 002-custom-geo-logic.md
│       ├── 003-httponly-cookies.md
│       └── 005-geospatial-prefiltering.md
│
├── 03-technical/               ← Implementación Detallada
│   ├── database-schema.md      ← Diccionario de Datos (14 Tablas)
│   ├── api-endpoints.md        ← Catálogo Completo de la API
│   └── testing-strategy.md     ← QA y Cobertura >= 90%
│
├── 04-state/                   ← Estado de la Misión
│   ├── backlog-y-bugs.md       ← Pendientes y Deuda Técnica
│   └── changelog.md            ← Historial de Versiones
│
└── 05-operations/              ← Despliegue y Mantenimiento
    ├── environment.md          ← Configuración .env y Secretos
    ├── deployment-rpi5.md      ← Guía de Instalación y Caddy
    └── security/               ← Políticas, Caddyfile y Análisis

---

## Regla de Documentación

**Todo cambio en código debe reflejar su documentación correspondiente.**

### Cuándo actualizar docs

| Tipo de cambio | Documentos a actualizar |
|---------------|-------------------------|
| Nueva feature | `01-product/` (user-stories), `03-technical/` (api-endpoints) |
| Nuevo patrón backend | `02-architecture/conventions.md` |
| Nuevo patrón frontend | `02-architecture/frontend-patterns.md` |
| Nuevo error HTTP | `02-architecture/error-codes.md` |
| Cambio en testing | `03-technical/testing-strategy.md` |
| Cambio en deployment | `05-operations/deployment-rpi5.md` |

### SDD y Documentación

En el ciclo SDD:
- **sdd-spec**: Define qué documentación se necesita
- **sdd-tasks**: Incluye tareas de documentación
- **sdd-verify**: Verifica que docs exista y esté completa
- **sdd-archive**: Archiva cambios junto con documentos

### Excepción

No requiere documentación:
- Refactors sin cambio de comportamiento
- Bug fixes sin cambio observable
- Cambios menores de estilo (sin impacto UX)