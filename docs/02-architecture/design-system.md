# Design System & UI/UX Patterns: Premium Edition

Este documento define la identidad visual de AgendaZonal, priorizando una estética **Premium**, moderna y de alta fidelidad, optimizada para rendimiento en móviles.

## Design Tokens (Premium Palette)

No usamos colores básicos. Utilizamos una paleta basada en HSL para mayor armonía y control.

| Token | HSL / CSS Var | Usage |
|-------|---------------|-------|
| `primary-hsl` | `221, 83%, 53%` | Color base de la marca (#2563eb) |
| `primary-gradient` | `linear-gradient(135deg, hsl(221, 83%, 53%), hsl(221, 83%, 45%))` | Botones principales y acciones destacadas |
| `glass-bg` | `rgba(255,255,255,0.7)` | Navbar y elementos flotantes (con `backdrop-blur-md`) |
| `surface-card` | `var(--surface-card)` | Fondo de tarjetas (Adaptativo: Blanco / Slate-900) |
| `danger-vibrant` | `0, 84%, 60%` | Alertas críticas y acciones de eliminación |
| `pulse-subtle` | `animation` | Efecto de carga para Skeletons Premium |

---

## UI Components Standards

### 1. Glassmorphism Effects
Para elementos flotantes (navbars, cards sobre mapas), aplicar:
- `bg-white/70 backdrop-blur-md border border-white/20`.
- Shadow: `shadow-[0_8px_32px_0_rgba(31,38,135,0.07)]`.

### 3. Premium Buttons (`.primary-btn`)
Los botones principales utilizan:
- Fondo: `primary-gradient`.
- Bordes: Redondeados `rounded-xl` o `rounded-2xl`.
- Interacción: Hover escala `1.05`, Active escala `0.95`.
- Sombras: `shadow-blue-500/20` con elevación suave.

### 4. Typography & Contrast
- **Headings**: `font-black` (900) con `tracking-tight` para un look moderno y contundente.
- **Contrast**: El texto principal (`text-[var(--text-main)]`) se ajusta automáticamente entre Slate-900 y Slate-100 según el modo.

---

## Interaction Patterns (Micro-animations)

### Hover & Active States
- **Scale**: Los botones principales deben escalar ligeramente (`scale-95`) al ser clickeados.
- **Transición**: Usar siempre `duration-300 ease-out`.

### Feedback Core
- **Loading Skeletons**: Prohibido usar "Cargando...". Usar placeholders animados que imiten la estructura de la card.
- **Haptic (Mobile)**: Al completar una acción crítica (ej: enviar reseña), disparar feedback visual suave (expand-fade).

---

## PWA & Responsive Patterns

### Mobile-First Layout
- **Safe Area**: Respetar `env(safe-area-inset-bottom)` para el menú inferior.
- **Gestos**: Las galerías de imágenes deben ser "swipeables" Nativamente.

---

## Accessibility
- **Contrast Ratio**: Mínimo 7:1 para legibilidad máxima en exteriores (Rosario al sol).
- **Interactive Targets**: Target mínimo de **48x48px**.
---

## Lessons Learned & Best Practices (Premium Migration)

Durante la migración a la estética Premium (v1.2.1), se establecieron las siguientes lecciones clave:

1. **HSL over Hex**: El uso de variables HSL (`--primary-hsl`) es obligatorio para temas reactivos. Permite invertir la luminosidad en modo oscuro manteniendo la coherencia de marca y generar transparencias dinámicas (HSLA) sin duplicar definiciones de color.
2. **Glassmorphism Triad**: Para un efecto de alta fidelidad, no basta con el desenfoque. Se requiere la combinación de `backdrop-filter: blur(12px)`, un fondo con opacidad controlada (`bg-white/70`) y un **borde sutil** (`border-white/20`) para dar definición.
3. **Perceived Performance**: Los **Skeleton Screens** animados con la estructura real del componente son superiores a los indicadores de carga genéricos, ya que reducen la carga cognitiva del usuario durante la espera.
4. **Semantic Abstraction**: En entornos de Vanilla JS con plantillas literales, es fundamental abstraer cadenas largas de clases de Tailwind en clases CSS semánticas (ej: `.primary-btn`, `.glass-bg`) para facilitar el mantenimiento y evitar la divergencia visual.
5. **Standalone Tooling**: El uso de binarios independientes (`tailwindcss.exe`) garantiza la continuidad del flujo de trabajo en entornos con restricciones de ejecución o hardware específico (Raspberry Pi).

