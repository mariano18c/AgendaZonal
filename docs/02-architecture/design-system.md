# Design System & UI/UX Patterns

## Design Tokens

### Color Palette (Tailwind)
| Token | Hex | Usage |
|-------|-----|-------|
| `blue-600` | #2563eb | Primary Action, Branding |
| `green-600` | #16a34a | Success, Verified Badges |
| `amber-500` | #f59e0b | Flash Offers, Warnings |
| `red-600` | #dc2626 | Critical Errors, Deletion |
| `gray-900` | #111827 | Headings, Main Text |
| `gray-600` | #4b5563 | Body Text |

### Typography
- **Font Stack**: Default System Sans (Inter fallback).
- **Style**: Mobile-first emphasis. Títulos en `font-bold`, Cuerpo en `leading-relaxed`.

---

## UI Components Standards

### Buttons
- **Primary**: `bg-blue-600 text-white hover:bg-blue-700`
- **Secondary**: `bg-gray-100 text-gray-700 hover:bg-gray-200`
- **Ghost**: `text-blue-600 hover:bg-blue-50`

### Cards
- **Provider Card**: `rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow`

---

## Interaction Patterns (UX)

### Tone & Voice
- **Estilo**: Voseo Rioplatense ("Buscá", "Encontrá tus servicios").
- **Claridad**: Evitar tecnicismos en la UI. "Rubros" en lugar de "Categorías".

### Feedback Core
- **Loading States**: Uso obligatorio de `animate-spin` en botones durante peticiones async.
- **Empty States**: Mensajes claros con "Call to Action" alternativos.
- **Error Handling**: Toasts rojos en el bottom-center para API failures.

---

## PWA & Performance
- **Offline Fallback**: `offline.html` precacheado.
- **Image Strategy**: Max-width 1200px, JPEG format, Lazy-loading nativo (`loading="lazy"`).
- **Map Interaction**: Minimizar refrescos del mapa Leaflet; usar `MarkerCluster` para alta densidad.

---

## Accessibility
- **Contraste**: Ratio mínimo 4.5:1 para texto legible.
- **Interactive Areas**: Target mínimo de 44px para móviles.
- **Aria**: Uso estricto de `aria-label` en botones de iconos (ej: WhatsApp share).
