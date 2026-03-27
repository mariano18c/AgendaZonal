# Proposal: setup-proyecto-base

## Metadata
- **Fecha**: 2026-03-20
- **Autor**: MarianoC
- **Estado**: pending_approval

## Overview
Definir el stack tecnológico y estructura base del proyecto Agenda Zonal para comenzar desarrollo.

## Motivation
El proyecto está vacío y sin定义 de tecnología. Necesitamos establecer las bases antes de implementar features.

## Proposed Approach

### Opción A: TypeScript/Node.js (Web CLI)
- **Ventajas**: Flexible, muchas librerías, ecosystem maduro
- **Uso**: CLI tools, APIs, automation scripts
- **Tools**: Bun/npm, ESLint, Prettier, Vitest

### Opción B: Python
- **Ventajas**: Simplicidad, data science, automation
- **Uso**: Scripts, APIs, ML/AI
- **Tools**: Poetry/pip, ruff, pytest

### Opción C: Go
- **Ventajas**: Binarios estáticos, performance, simple
- **Uso**: CLIs, APIs, microservices
- **Tools**: go mod, golangci-lint, testing

### Opción D: Rust
- **Ventajas**: Performance máximo, memory safety
- **Uso**: CLIs high-performance, systems programming
- **Tools**: cargo, clippy, rustfmt

## Recommendation
**Opción A: TypeScript/Node.js** - Recomendado para:
- Curva de aprendizaje accesible
- Flexibilidad para diferentes tipos de aplicaciones
- Integración con OpenCode y gentle-ai

## Next Steps (si se aprueba)

1. **Spec**: Escribir SPEC-002-setup-proyecto-base.md
2. **Design**: Diseñar estructura y herramientas
3. **Tasks**: Descomponer en tareas de setup

## Questions for User

1. ¿Tenés alguna preferencia de lenguaje/framework?
2. ¿Qué tipo de aplicación va a ser este proyecto?
3. ¿Hay algún requerimiento específico?

---

**¿Querés proceder con una de estas opciones o preferís otra?**