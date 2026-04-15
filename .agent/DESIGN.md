# Design System - AgendaZonal

## Color Palette

### Primary Colors
| Class | Hex | Usage |
|-------|-----|-------|
| `text-blue-600` | #2563eb | Links, primary actions |
| `bg-blue-600` | #2563eb | Buttons, badges |
| `bg-blue-50` | #eff6ff | Light backgrounds |

### Semantic Colors
| Class | Hex | Usage |
|-------|-----|-------|
| `text-green-600` | #16a34a | Success states, verified |
| `text-red-600` | #dc2626 | Errors, delete actions |
| `text-yellow-600` | #ca8a04 | Warnings, pending |
| `text-gray-500` | #6b7280 | Secondary text |

### Neutral Colors
| Class | Hex | Usage |
|-------|-----|-------|
| `text-gray-900` | #111827 | Headings, primary text |
| `text-gray-700` | #374151 | Body text |
| `text-gray-500` | #6b7280 | Secondary text |
| `text-gray-400` | #9ca3af | Placeholder, disabled |
| `bg-gray-50` | #f9fafb | Card backgrounds |
| `border-gray-200` | #e5e7eb | Borders |

## Typography

### Font Family
- **System default**: `font-sans` (system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto)

### Font Sizes
| Class | Size | Usage |
|-------|------|-------|
| `text-xs` | 0.75rem | Labels, captions |
| `text-sm` | 0.875rem | Secondary text |
| `text-base` | 1rem | Body text |
| `text-lg` | 1.125rem | Emphasized body |
| `text-xl` | 1.25rem | Section titles |
| `text-2xl` | 1.5rem | Page titles |
| `text-3xl` | 1.875rem | Hero text |

### Font Weights
| Class | Weight | Usage |
|-------|--------|-------|
| `font-light` | 300 | Decorative |
| `font-normal` | 400 | Body |
| `font-medium` | 500 | Emphasis |
| `font-semibold` | 600 | Headings |
| `font-bold` | 700 | Strong emphasis |

## Spacing System

### Common Spacing
| Class | Size | Usage |
|-------|------|-------|
| `p-2` | 0.5rem | Compact padding |
| `p-4` | 1rem | Standard padding |
| `p-6` | 1.5rem | Section padding |
| `gap-2` | 0.5rem | Grid/gap spacing |
| `gap-4` | 1rem | Standard gap |
| `space-y-4` | 1rem | Vertical spacing |

## Components

### Cards
```html
<div class="bg-white rounded-lg shadow p-6">
  <!-- Card content -->
</div>
```

### Buttons
```html
<!-- Primary -->
<button class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
  Acción
</button>

<!-- Secondary -->
<button class="bg-gray-200 text-gray-700 px-4 py-2 rounded hover:bg-gray-300">
  Cancelar
</button>

<!-- Danger -->
<button class="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">
  Eliminar
</button>
```

### Badges
```html
<!-- Verification Badge -->
<span class="bg-green-100 text-green-800 px-2 py-1 rounded text-xs font-medium">
  ✓ Verificado
</span>

<!-- Status Badge -->
<span class="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs font-medium">
  Pendiente
</span>
```

### Form Inputs
```html
<input class="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
```

### Links
```html
<a href="/" class="text-blue-600 hover:text-blue-800 hover:underline">
  Texto
</a>
```

## Component States

### Loading State
```html
<div class="animate-pulse">
  <div class="h-4 bg-gray-200 rounded w-3/4"></div>
</div>
```

### Empty State
```html
<div class="text-center py-12">
  <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
  </svg>
  <p class="mt-2 text-gray-500">No hay elementos</p>
</div>
```

### Error State
```html
<div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
  <p>Mensaje de error</p>
</div>
```

### Success State
```html
<div class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
  <p>Operación exitosa</p>
</div>
```

## Responsive Breakpoints

| Breakpoint | Width | Usage |
|------------|-------|-------|
| `sm` | 640px | Small phones |
| `md` | 768px | Tablets |
| `lg` | 1024px | Laptops |
| `xl` | 1280px | Desktops |

### Mobile-First Pattern
```html
<!-- Mobile first, then tablet+ -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  <!-- Cards -->
</div>
```

## Map Styles

### Leaflet Integration
```javascript
// Map container
<div id="map" class="h-64 w-full rounded-lg"></div>

// Marker
L.marker([lat, lon]).addTo(map).bindPopup('Content');
```

### Map Controls
- Zoom controls: default position (top-left)
- Layer control: optional, top-right
- Geolocation: button in control

## Icons

### Using Inline SVG (Preferred)
```html
<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M..." />
</svg>
```

### Icon Sizes
| Class | Size |
|-------|------|
| `w-4 h-4` | Small (16px) |
| `w-5 h-5` | Medium (20px) |
| `w-6 h-6` | Large (24px) |
| `w-8 h-8` | XL (32px) |
