# Tasks: Migración a Estética Premium

## Phase 1: Foundation (Config & Global CSS)

- [x] 1.1 Configurar `frontend/tailwind.config.js` con extensiones para `colors` (tokens HSL) y `backgroundImage` (gradientes).
- [x] 1.2 Implementar variables CSS `:root` y bloque `.dark` en `frontend/css/styles.css` siguiendo el Design System.
- [x] 1.3 Definir utilidades `.glass-bg`, `.primary-gradient` y animaciones de pulso para skeletons en `frontend/css/styles.css`.
- [x] 1.4 Ejecutar build de Tailwind para verificar la integración de los nuevos tokens en `output.css`.

## Phase 2: Core Components Implementation (JS)

- [x] 2.1 Actualizar `renderSkeleton` en `frontend/js/app.js` para aplicar estilos premium y animaciones de pulso.
- [x] 2.2 Refactorizar `renderCard` y `renderBadge` en `frontend/js/app.js` para usar tokens HSL y bordes sutiles.
- [x] 2.3 Modificar `updateNavbar` en `frontend/js/app.js` para inyectar la clase `glass-bg` y estilos de botón premium.

## Phase 3: Integration & Layout Refactor (HTML)

- [x] 3.1 Actualizar `frontend/index.html`: aplicar `glass-bg` a `<nav>` y `primary-gradient` a botones de búsqueda.
- [x] 3.2 Sincronizar `frontend/login.html` y `frontend/register.html` con los nuevos estándares de botones y inputs.
- [x] 3.3 Revisar `frontend/profile.html` y `frontend/search.html` para asegurar coherencia visual completa.

## Phase 4: Verification & Polish

- [x] 4.1 Test Visual: Verificar efecto de blur y sombras en `backdrop-filter` sobre diferentes fondos.
- [x] 4.2 Test de Contraste: Validar ratio >= 7:1 en componentes principales usando herramientas de dev (Lighthouse/Axe).
- [x] 4.3 Test de Modo Oscuro: Asegurar que la transición de tokens HSL sea fluida y sin "flashes" de colores estándar.
