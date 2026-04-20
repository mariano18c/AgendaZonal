/docs
│
├── 00-context/                 ← Identidad y Contexto Maestro
│   ├── AI-MASTER-PROMPT.md     ← Perfil del Agente
│   ├── project-brief.md        ← Visión, Stack y Límites RPi 5
│   └── sdd-lifecycle/          ← Historial SDD (SPECS, ARCHIVE, TASKS)
│
├── 01-product/                 ← Estrategia y Requerimientos
│   ├── vision-y-negocio.md
│   ├── user-stories.md
│   └── roadmap.md
│
├── 02-architecture/            ← Decisiones y Estándares
│   ├── design-system.md        ← UIX, Tailwind y PWA Patterns
│   ├── conventions.md          ← Backend Patterns y Clean Code
│   └── adr/                    ← Architecture Decision Records
│       ├── 001-sqlite-over-pg.md
│       ├── 002-custom-geo-logic.md
│       └── 003-httponly-cookies.md
│
├── 03-technical/               ← Implementación Detallada
│   ├── database-schema.md      ← Diccionario de Datos
│   ├── api-endpoints.md        ← Catálogo de API
│   └── testing-strategy.md     ← QA y Cobertura
│
├── 04-state/                   ← Estado de la Misión
│   ├── backlog-y-bugs.md       ← Pendientes y Deuda Técnica
│   └── changelog.md            ← Registro de Cambios
│
└── 05-operations/              ← Despliegue y Mantenimiento
    ├── environment.md          ← Configuración .env
    ├── deployment-rpi5.md      ← Guía de Instalación y Caddy
    └── security/               ← Políticas y Análisis de Seguridad