# Frontend Patterns

Este documento describe los patrones JavaScript usados en el frontend.

## XSS Prevention

### escapeHtml()
Previene XSS sanitizando texto antes de renderizar.

```javascript
function escapeHtml(text) {
  if (text == null) return '';
  const div = document.createElement('div');
  div.textContent = String(text);
  return div.innerHTML;
}

// Uso
const safeName = escapeHtml(userInput);
element.innerHTML = `<div>${safeName}</div>`;
```

**Regla**: TODO input de usuario debe passar por `escapeHtml()` antes de `innerHTML`.

## Loading States

### Skeleton Loading
Muestra skeleton mientras carga datos.

```javascript
function renderSkeleton({type, count = 1}) {
  if (type === 'card') {
    return Array(count).fill(`
      <div class="bg-white rounded-lg shadow-sm border p-4 animate-pulse">
        <div class="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
        <div class="h-3 bg-gray-200 rounded w-1/2"></div>
      </div>
    `).join('');
  }
  // ...
}

// Uso
grid.innerHTML = renderSkeleton({type: 'card', count: 6});
```

### Spinner
Spinner simple para acciones.

```javascript
function showSpinner() {
  document.getElementById('spinner').classList.remove('hidden');
}

function hideSpinner() {
  document.getElementById('spinner').classList.add('hidden');
}
```

## State Management

### Simple Observer
Para cambios cross-component.

```javascript
// Observador simple
const observers = new Map();

function observe(key, callback) {
  if (!observers.has(key)) observers.set(key, []);
  observers.get(key).push(callback);
}

function notify(key, data) {
  observers.get(key)?.forEach(cb => cb(data));
}

// Uso
observe('userLoggedIn', (user) => {
  updateNavbar();
  loadUserData();
});
notify('userLoggedIn', user);
```

## API Calls

### apiRequest()
Wrapper con manejo de errores.

```javascript
async function apiRequest(url, options = {}) {
  const token = localStorage.getItem('token');
  
  const resp = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? {Authorization: `Bearer ${token}`} : {}),
      ...options.headers
    }
  });
  
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || 'Error en la solicitud');
  }
  
  return resp.json();
}
```

## Token Storage

```javascript
function getToken() {
  return localStorage.getItem('token');
}

function setToken(token) {
  localStorage.setItem('token', token);
}

function clearToken() {
  localStorage.removeItem('token');
}
```

## Component Patterns

### renderEmptyState()
Estado vacío para grids.

```javascript
function renderEmptyState({emoji, title, subtitle, cta}) {
  return `
    <div class="text-center py-10">
      <div class="text-4xl mb-4">${emoji}</div>
      <h3 class="text-lg font-semibold">${title}</h3>
      <p class="text-gray-500 mt-1">${subtitle}</p>
      ${cta ? `<button onclick="${cta.onClick}" class="mt-4 text-blue-600">${cta.label}</button>` : ''}
    </div>
  `;
}
```

### renderBadge()
Badge de verificación.

```javascript
function renderBadge({text, variant = 'info'}) {
  const colors = {
    success: 'bg-green-100 text-green-700',
    warning: 'bg-yellow-100 text-yellow-700',
    error: 'bg-red-100 text-red-700',
    info: 'bg-blue-100 text-blue-700'
  };
  return `<span class="px-2 py-1 rounded-full text-xs ${colors[variant]}">${text}</span>`;
}
```