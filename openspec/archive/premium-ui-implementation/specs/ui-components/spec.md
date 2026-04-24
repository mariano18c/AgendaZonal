# UI Components Specification

## Purpose
Estandarizar el comportamiento visual y las micro-interacciones de los componentes básicos de la interfaz.

## Requirements

### Requirement: Estados de Interacción de Botones
Los botones principales MUST proporcionar feedback visual inmediato al interactuar.

#### Scenario: Click en botón principal
- GIVEN un botón con `primary-gradient`
- WHEN el usuario hace click (estado active)
- THEN el botón debe escalar ligeramente (`scale-95`)
- AND la transición debe durar 300ms con curva `ease-out`

### Requirement: Skeletons Animados
El sistema SHALL mostrar placeholders animados en lugar de texto estático "Cargando" para estados asíncronos.

#### Scenario: Carga de categorías
- GIVEN el inicio de una petición a la API
- WHEN los datos aún no han retornado
- THEN el contenedor debe mostrar elementos `skeleton-card` con animación de pulso
- AND la estructura del skeleton debe imitar la forma final de la tarjeta de categoría
