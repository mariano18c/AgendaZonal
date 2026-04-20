# Design System & UI/UX Patterns: Premium Edition

Este documento define la identidad visual de AgendaZonal, priorizando una estética **Premium**, moderna y de alta fidelidad, optimizada para rendimiento en móviles.

## Design Tokens (Premium Palette)

No usamos colores básicos. Utilizamos una paleta basada en HSL para mayor armonía y control.

| Token | HSL | Usage |
|-------|-----|-------|
| `primary-gradient` | `linear-gradient(135deg, #2563eb, #1d4ed8)` | Brand actions, Main Buttons |
| `success-soft` | `hsl(142, 70%, 95%)` | Background for success banners |
| `danger-vibrant` | `hsl(0, 84%, 60%)` | Critical errors, Deletion |
| `glass-bg` | `rgba(255, 255, 255, 0.7)` | Navbar, Overlays (require `backdrop-filter`) |
| `surface-900` | `hsl(222, 47%, 11%)` | Midnight mode surfaces |

---

## UI Components Standards

### 1. Glassmorphism Effects
Para elementos flotantes (navbars, cards sobre mapas), aplicar:
- `bg-white/70 backdrop-blur-md border border-white/20`.
- Shadow: `shadow-[0_8px_32px_0_rgba(31,38,135,0.07)]`.

### 2. Premium Typography
- **Headings**: `font-outfit` (fallback Sans) con `tracking-tight`.
- **Contrast**: El texto principal siempre debe ser `text-slate-900` sobre fondos claros.

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
- **Dark Mode**: Implementar mediante clases `dark:` respetando la paleta HSL invertida.

