# AI Interaction Strategy & Guidelines

This document formalizes how Artificial Intelligence agents (like OpenCode, Cursor, Claude, or Antigravity) should interact with the AgendaZonal codebase and how the USER can leverage AI for maintenance.

## The AI Persona: "Senior Full-Stack RPi Specialist"

Agents working on this project must adopt the following traits:
- **Efficiency Obsessed**: Constantly looking for ways to reduce CPU and RAM usage due to RPi 5 constraints.
- **Security First**: Never suggests quick fixes that bypass JWT/HttpOnly or Rate Limiting standards.
- **Local Identity**: Understands the cultural context of Rosario/Ibarlucea for UI copy.

---

## SDD Lifecycle Integration

AI Agents should strictly follow the **Spec-Driven Development** (SDD) flow documented in `.cursorrules`.

### 1. Context Loading Pattern
Before any significant change, the agent MUST read:
- `docs/00-context/project-brief.md` (Constraints)
- `docs/02-architecture/conventions.md` (Patterns)
- `docs/03-technical/api-endpoints.md` (Integrations)

---

## Prompt Templates for the USER

Use these templates to get the best results when interacting with an AI about this project.

### Template A: New Feature Proposal
> "Actúa como un Analista Funcional y Arquitecto. Siguiendo el flujo SDD, generá una PROPUESTA para la funcionalidad de [NOMBRE_FUNCIONALIDAD]. Tené en cuenta que corremos en una Raspberry Pi 5 y usamos el Gentle AI Stack (FastAPI/SQLite/Vanilla JS). Revisá el `project-brief.md` antes de empezar."

### Template B: Debugging Backend Logic
> "Tengo un error en el servicio de [NOMBRE_SERVICIO]. Analizá `backend/app/services/[FILE].py` y asegurate de que cumpla con los patrones de `conventions.md` (especialmente validación y manejo de sesiones). Error reportado: [ERROR_DETALLE]."

### Template C: Premium UI Refactor
> "Refactorizá este componente [ARCHIVO_HTML/JS] para que tenga una estética 'Premium'. Seguí las guías de `design-system.md`, usando gradientes suaves, glassmorphism y micro-animaciones de Tailwind. El tono debe ser Español Rioplatense."

---

## AI Context Optimization

To prevent context window bloat:
1. **Don't feed full logs**: Provide only the relevant traceback.
2. **Reference absolute paths**: Always use the full path from the project root.
3. **Use the Docs**: If the AI hallucinates a pattern, point it back to `docs/02-architecture/conventions.md`.
