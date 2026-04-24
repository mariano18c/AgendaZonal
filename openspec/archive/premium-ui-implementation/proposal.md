# Proposal: Migración a Estética Premium (Tokens HSL y Glassmorphism)

## Intent

Sincronizar el código real de la aplicación con la visión de diseño documentada en `docs/02-architecture/design-system.md`. Actualmente existe una brecha crítica: la documentación exige una estética "Premium" (HSL, glassmorphism, micro-animaciones) pero el código utiliza Tailwind estándar sin personalización, lo que degrada la percepción de calidad del producto.

## Scope

### In Scope
- Implementación de Design Tokens basados en HSL en `tailwind.config.js`.
- Definición de clases globales para Glassmorphism en `frontend/css/styles.css`.
- Actualización de componentes UI críticos (Navbar, Cards, Buttons) para usar los nuevos tokens.
- Implementación de estilos CSS para componentes de `app.js` (Skeletons, Badges).
- Refactorización de `index.html` y templates principales para eliminar clases de color "hardcoded".

### Out of Scope
- Rediseño completo de la experiencia de usuario (UX flows).
- Migración a un framework de componentes (React/Vue).
- Cambios en la lógica del Backend.

## Capabilities

### New Capabilities
- `design-tokens`: Gestión centralizada de colores y gradientes mediante variables HSL.
- `glassmorphism-system`: Utilidades de UI para efectos de transparencia y desenfoque de fondo.

### Modified Capabilities
- `ui-components`: Actualización de los estándares de visualización de componentes básicos (botones, tarjetas, badges).

## Approach

Seguiremos un enfoque de **Foundation-First**:
1. **Configuración**: Extender `tailwind.config.js` con la paleta HSL y gradientes definidos.
2. **Global CSS**: Definir variables CSS (`:root`) en `styles.css` para permitir cambios dinámicos y soporte de Glassmorphism.
3. **Componentes**: Actualizar `app.js` para que los componentes generados dinámicamente inyecten las clases Premium.
4. **Refactor**: Reemplazar clases Tailwind estándar (`bg-blue-600`) por los nuevos tokens (`bg-primary-gradient`).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/tailwind.config.js` | Modified | Configuración de tokens y extensiones de tema. |
| `frontend/css/styles.css` | Modified | Definición de variables CSS y utilidades personalizadas. |
| `frontend/js/app.js` | Modified | Actualización de templates de componentes (Cards, Skeletons). |
| `frontend/index.html` | Modified | Aplicación de nuevos estilos en la estructura base. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Inconsistencia visual | High | Aplicar cambios en lotes atómicos por componente. |
| Problemas de contraste | Low | Verificar ratios contra el standard WCAG (7:1) definido. |
| Rendimiento en RPi 5 | Low | El uso de `backdrop-filter` es ligero en navegadores modernos, pero se monitoreará el consumo de CPU. |

## Rollback Plan

Revertir cambios mediante Git a la rama `main`. Dado que es un cambio puramente estético (CSS/JS front), el impacto en datos es nulo.

## Dependencies

- Navegadores modernos con soporte para `backdrop-filter` y variables CSS (estándar en RPi 5).

## Success Criteria

- [ ] Los botones y acciones principales usan `primary-gradient`.
- [ ] La Navbar y Overlays utilizan `glass-bg` con desenfoque de fondo.
- [ ] No quedan referencias a `bg-blue-600` o `text-gray-900` estándar en los archivos modificados.
- [ ] El linter de CSS no arroja errores sobre variables indefinidas.
