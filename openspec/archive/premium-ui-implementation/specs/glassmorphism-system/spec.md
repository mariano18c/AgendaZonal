# Glassmorphism System Specification

## Purpose
Definir los estándares para efectos de transparencia y desenfoque de fondo, proporcionando profundidad visual sin comprometer la legibilidad.

## Requirements

### Requirement: Efecto Glass-BG
Los elementos flotantes (navbars, modales, overlays) MUST soportar el efecto de glassmorphism.

#### Scenario: Aplicación en Navbar
- GIVEN una Navbar con la clase `glass-bg`
- WHEN el usuario hace scroll y hay contenido debajo de la Navbar
- THEN el fondo de la Navbar debe mostrarse translúcido (`rgba(255, 255, 255, 0.7)`)
- AND debe aplicarse un desenfoque de fondo (`backdrop-filter: blur(12px)`)
- AND debe tener un borde sutil de 1px (`border-white/20`)

### Requirement: Sombras Premium
Los elementos con glassmorphism SHOULD utilizar sombras suaves de gran difusión para enfatizar la elevación.

#### Scenario: Elevación de Tarjeta
- GIVEN una tarjeta con efecto glass
- WHEN se renderiza sobre el fondo de la página
- THEN debe aplicar una sombra de tipo `shadow-[0_8px_32px_0_rgba(31,38,135,0.07)]`
