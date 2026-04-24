# Design: Migración a Estética Premium

## Technical Approach

Implementaremos un sistema de diseño híbrido que utiliza **CSS Variables** como fuente de verdad y las integra en **Tailwind CSS** mediante la propiedad `theme.extend`. Esto permite que la estética "Premium" sea reactiva (soporte nativo de modo oscuro) y fácil de aplicar en componentes dinámicos.

## Architecture Decisions

### Decision: Fuente de Verdad para Tokens
**Choice**: Definir tokens HSL en `:root` dentro de `styles.css`.
**Alternatives considered**: Definir colores estáticos directamente en `tailwind.config.js`.
**Rationale**: Las variables CSS permiten que `glass-bg` y gradientes cambien dinámicamente según el tema (light/dark) sin necesidad de re-compilar el CSS o duplicar clases.

### Decision: Implementación de Glassmorphism
**Choice**: Crear utilidades personalizadas en `styles.css` usando `@apply` de Tailwind.
**Alternatives considered**: Usar clases arbitrarias de Tailwind (`bg-white/70 backdrop-blur-md`) directamente en el HTML.
**Rationale**: Centralizar el "look & feel" de Glassmorphism en una clase `.glass-bg` facilita ajustes globales (ej: cambiar el nivel de blur) en un solo lugar, cumpliendo con el patrón "Premium Edition".

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/tailwind.config.js` | Modify | Extender el tema con los nuevos tokens (`primary-gradient`, `surface-900`, etc.) apuntando a variables CSS. |
| `frontend/css/styles.css` | Modify | Definir los valores HSL en `:root` y crear utilidades `.glass-bg` y `.primary-gradient`. |
| `frontend/js/app.js` | Modify | Actualizar funciones `renderSkeleton`, `renderCard` y `renderBadge` para usar las nuevas clases. |
| `frontend/index.html` | Modify | Reemplazar clases de colores base por tokens semánticos en el layout principal. |

## Interfaces / Contracts

### CSS Variables Bridge
```css
:root {
  --primary-hue: 222;
  --primary-sat: 84%;
  --primary-light: 50%;
  
  --glass-bg: rgba(255, 255, 255, 0.7);
  --glass-border: rgba(255, 255, 255, 0.2);
}

.dark {
  --glass-bg: rgba(17, 24, 39, 0.7);
  --glass-border: rgba(255, 255, 255, 0.1);
}
```

### Tailwind Extension
```javascript
theme: {
  extend: {
    colors: {
      'surface-900': 'hsl(222, 47%, 11%)',
      'danger-vibrant': 'hsl(0, 84%, 60%)',
    },
    backgroundImage: {
      'primary-gradient': 'linear-gradient(135deg, #2563eb, #1d4ed8)',
    }
  }
}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Visual | Contraste y Blur | Verificación manual en Chrome/Edge para asegurar que `backdrop-filter` se aplique correctamente. |
| Build | Compilación de Tailwind | Ejecutar `npm run build` para asegurar que las nuevas clases no rompan el pipeline de PostCSS. |
| Theme | Modo Oscuro | Alternar el tema y verificar que las variables HSL cambien sus valores. |

## Migration / Rollout

No requiere migración de datos. Es una actualización puramente estética de la capa de presentación.

## Open Questions

- [ ] ¿Deberíamos incluir un fallback para navegadores que no soportan `backdrop-filter`? (Probablemente no sea necesario para el target de este proyecto).
