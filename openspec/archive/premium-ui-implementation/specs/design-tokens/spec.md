# Design Tokens Specification

## Purpose
Establecer un sistema centralizado de tokens visuales basados en HSL para garantizar una estética premium coherente y facilitar el mantenimiento del tema.

## Requirements

### Requirement: Paleta de Colores HSL
El sistema MUST utilizar una paleta de colores definida exclusivamente en formato HSL para permitir variaciones de luminosidad y saturación consistentes.

#### Scenario: Uso de tokens en componentes
- GIVEN la configuración de Tailwind extendida con tokens HSL
- WHEN un elemento utiliza la clase `bg-primary-gradient`
- THEN el elemento debe mostrar el gradiente de marca definido (135deg, #2563eb, #1d4ed8)
- AND el texto sobre este fondo debe mantener un contraste >= 7:1

### Requirement: Soporte de Modo Oscuro con Tokens
El sistema SHALL invertir los valores de luminosidad de los tokens HSL cuando el modo oscuro esté activo (`html.dark`).

#### Scenario: Cambio automático de tono
- GIVEN el modo oscuro activado
- WHEN un componente utiliza el token `surface-900`
- THEN el fondo del componente debe mostrar el color Midnight definido (`hsl(222, 47%, 11%)`)
