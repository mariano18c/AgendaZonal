function getThemePreference() {
  const saved = localStorage.getItem('theme');
  if (saved) return saved;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme) {
  const html = document.documentElement;
  if (theme === 'dark') {
    html.classList.add('dark');
  } else {
    html.classList.remove('dark');
  }
}

function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.classList.contains('dark');
  const newTheme = isDark ? 'light' : 'dark';
  localStorage.setItem('theme', newTheme);
  applyTheme(newTheme);
}

function initTheme() {
  applyTheme(getThemePreference());
}

async function updateNavbar() {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;

  const isDark = document.documentElement.classList.contains('dark');
  const themeToggle = `<button onclick="toggleTheme()" class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition" title="${isDark ? 'Modo claro' : 'Modo oscuro'}">${isDark ? '☀️' : '🌙'}</button>`;

  const isLoggedIn = !!localStorage.getItem('token');
  const user = JSON.parse(localStorage.getItem('user') || 'null');

  if (isLoggedIn && user) {
    let unreadHtml = '';
    try {
      const data = await apiRequest('/api/notifications/unread-count');
      if (data && data.unread_count > 0) {
        unreadHtml = `<span class="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full ml-1 translate-y-[-2px]">${data.unread_count}</span>`;
      }
    } catch(e) {
      // Ignorar errores silenciosamente si expira el token
    }
    let adminLink = '';
    
    // Admin/moderator links
    if (user.role === 'admin' || user.role === 'moderator') {
      adminLink = `
        <a href="/pending" class="text-yellow-600 hover:text-yellow-800">⏳ Pendientes</a>
        <a href="/dashboard" class="text-gray-600 hover:text-gray-800 flex items-center">📊 Dashboard${unreadHtml}</a>
        <a href="/admin/reviews" class="text-gray-600 hover:text-gray-800">⭐ Reseñas</a>
        <a href="/admin/reports" class="text-gray-600 hover:text-gray-800">🚩 Reportes</a>
        <a href="/admin/analytics" class="text-gray-600 hover:text-gray-800">📊 Analytics</a>
        <a href="/admin/utilities" class="text-gray-600 hover:text-gray-800">🏥 Teléfonos</a>
        ${user.role === 'admin' ? `<a href="/admin/users" class="text-gray-600 hover:text-gray-800">👥 Usuarios</a>` : ''}
      `;
    } else {
      adminLink = `<a href="/dashboard" class="text-gray-600 hover:text-gray-800 flex items-center">📊 Dashboard${unreadHtml}</a>`;
    }
    
    const pushBtnHtml = ('Notification' in window && Notification.permission !== 'granted' && Notification.permission !== 'denied')
      ? `<button id="pwaPushBtn" onclick="handleManualPushSubscription()" class="text-purple-600 hover:text-purple-800 transition text-sm font-medium" title="Activar notificaciones">🔔 Notificaciones</button>`
      : '';

    navbar.innerHTML = `
      <div class="flex items-center gap-4">
        ${themeToggle}
        <span class="text-gray-700 dark:text-gray-200">Hola, ${user.username}</span>
        <a href="/contact-form?mode=add" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition">Agregar</a>
        ${adminLink}
        ${pushBtnHtml}
        <button id="pwaInstallBtn" class="hidden text-green-600 hover:text-green-800" title="Instalar app">📲 Instalar</button>
        <button onclick="logout()" class="text-gray-600 hover:text-gray-800 dark:text-gray-300 dark:hover:text-gray-100">Salir</button>
      </div>
    `;
  } else {
    navbar.innerHTML = `
      <div class="flex items-center gap-4">
        ${themeToggle}
        <a href="/login" class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300">Iniciar sesión</a>
        <a href="/register" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition">Registrarse</a>
      </div>
    `;
  }
}

function showAlert(message, type = 'error') {
  const alertDiv = document.createElement('div');
  alertDiv.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 ${
    type === 'error' ? 'bg-red-500 text-white' : 'bg-green-500 text-white'
  }`;
  alertDiv.textContent = message;
  document.body.appendChild(alertDiv);
  setTimeout(() => alertDiv.remove(), 3000);
}

// ============================================
// Reusable approval/rejection UX pattern
// ============================================
let alertTimeout = null;

/**
 * Show inline alert message (replaces page content for better visibility)
 * @param {string} message - The message to display
 * @param {string} type - 'success', 'error', or 'warning'
 * @param {string} containerId - Optional container ID (defaults to 'mainContent')
 */
function showInlineAlert(message, type, containerId = 'content') {
  const container = document.getElementById(containerId);
  if (!container) {
    // Fallback to showAlert if no container found
    showAlert(message, type);
    return;
  }
  
  const existingAlert = container.querySelector('.inline-alert');
  if (existingAlert) existingAlert.remove();

  const alertDiv = document.createElement('div');
  alertDiv.className = `inline-alert mb-4 rounded-lg p-4 text-center font-medium ${
    type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' :
    type === 'error' ? 'bg-red-50 text-red-800 border border-red-200' :
    'bg-yellow-50 text-yellow-800 border border-yellow-200'
  }`;
  alertDiv.textContent = message;
  
  // Insert at the top of container
  container.insertBefore(alertDiv, container.firstChild);

  if (alertTimeout) clearTimeout(alertTimeout);
  alertTimeout = setTimeout(() => alertDiv.remove(), 5000);
}

/**
 * Set button loading state
 * @param {HTMLElement} btn - The button element
 * @param {boolean} loading - True to show loading, false to restore
 */
function setButtonLoading(btn, loading) {
  if (!btn) return;
  
  if (loading) {
    btn.dataset.originalText = btn.textContent;
    btn.textContent = 'Procesando...';
    btn.disabled = true;
    btn.classList.add('opacity-50', 'cursor-not-allowed');
  } else {
    btn.textContent = btn.dataset.originalText || btn.textContent;
    btn.disabled = false;
    btn.classList.remove('opacity-50', 'cursor-not-allowed');
  }
}

/**
 * Generic action handler for approve/reject operations
 * @param {Function} apiCall - Async function that performs the action
 * @param {string} successMessage - Message to show on success
 * @param {Function} onSuccess - Optional callback on success (e.g., reload data)
 * @param {Event} event - The click event
 */
async function handleAction(apiCall, successMessage, onSuccess, event) {
  const btn = event.target.closest('button');
  const card = btn?.closest('.bg-white');
  
  // Show processing state
  if (btn) setButtonLoading(btn, true);
  if (card) card.classList.add('opacity-50');

  try {
    await apiCall();
    showInlineAlert(successMessage, 'success');
    
    if (onSuccess) {
      await onSuccess();
    }
  } catch (err) {
    showInlineAlert('Error: ' + err.message, 'error');
    if (card) card.classList.remove('opacity-50');
  } finally {
    if (btn) setButtonLoading(btn, false);
  }
}

function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('es-AR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  updateNavbar();

  // --- PWA: Register Service Worker ---
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').then((reg) => {
      console.log('SW registered:', reg.scope);
    }).catch((err) => {
      console.warn('SW registration failed:', err);
    });
  }

  // --- PWA: Install prompt ---
  let deferredPrompt = null;
  const installBtn = document.getElementById('pwaInstallBtn');

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    if (installBtn) installBtn.classList.remove('hidden');
  });

  if (installBtn) {
    installBtn.addEventListener('click', async () => {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        console.log('PWA installed');
      }
      deferredPrompt = null;
      installBtn.classList.add('hidden');
    });
  }

  // --- Push Notifications: auto-subscribe if already granted ---
  if ('PushManager' in window && 'serviceWorker' in navigator && isLoggedIn()) {
    if ('Notification' in window && Notification.permission === 'granted') {
      console.log('Push: Permission already granted, attempting silent subscribe...');
      navigator.serviceWorker.ready.then(reg => {
        return subscribeToPush();
      }).catch(err => console.warn('Push: Auto-subscribe error:', err));
    } else {
      console.log('Push: Manual subscription required (permission not granted)');
    }
  } else {
    console.log('Push: Skipped - not logged in or no push support');
  }
});

async function handleManualPushSubscription() {
  const btn = document.getElementById('pwaPushBtn');
  if (btn) {
    btn.disabled = true;
    btn.textContent = '⏱️ Activando...';
  }
  
  if ('Notification' in window) {
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      try {
        const sub = await subscribeToPush();
        if (sub) {
          showAlert('Notificaciones activadas exitosamente', 'success');
          if (btn) btn.remove(); // Remove button once subscribed
        } else {
          showAlert('No se pudo completar la suscripción (Revisa claves VAPID).');
          if (btn) { btn.disabled = false; btn.textContent = '🔔 Notificaciones'; }
        }
      } catch (err) {
        showAlert('Error: ' + err.message);
        if (btn) { btn.disabled = false; btn.textContent = '🔔 Notificaciones'; }
      }
    } else {
      showAlert('Permiso de notificaciones denegado.');
      if (btn) btn.remove();
    }
  }
}

/**
 * Subscribe to push notifications.
 * Returns the PushSubscription or null if not supported/denied.
 */
async function subscribeToPush() {
  console.log('subscribeToPush: Starting...');
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    console.log('subscribeToPush: Not supported');
    return null;
  }

  const reg = await navigator.serviceWorker.ready;
  console.log('subscribeToPush: SW ready');

  // Force re-subscription to clear potentially expired endpoints (410 Gone)
  let subscription = await reg.pushManager.getSubscription();
  if (subscription) {
      console.log('subscribeToPush: Unsubscribing existing to refresh...');
      await subscription.unsubscribe();
      // Also notify backend to remove old one if possible
  }

  // Get VAPID public key from backend
  let vapidPublicKey = window.__VAPID_PUBLIC_KEY__ || '';
  if (!vapidPublicKey) {
    console.log('subscribeToPush: Fetching VAPID key from backend...');
    try {
      const res = await apiRequest('/api/notifications/vapid-public-key');
      vapidPublicKey = res.public_key;
      window.__VAPID_PUBLIC_KEY__ = vapidPublicKey;
      console.log('subscribeToPush: Got VAPID key:', vapidPublicKey.substring(0, 30) + '...');
    } catch (e) {
      console.error('subscribeToPush: Could not fetch VAPID public key:', e);
      return null;
    }
  }
  if (!vapidPublicKey) {
    console.warn('Push: No VAPID public key configured');
    return null;
  }

  try {
    console.log('subscribeToPush: Calling pushManager.subscribe...');
    const convertedKey = urlBase64ToUint8Array(vapidPublicKey);
    
    subscription = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: convertedKey,
    });
    console.log('subscribeToPush: Browser subscription created:', subscription);
  } catch (err) {
    console.warn('Push: Subscription failed:', err.message);
    return null;
  }

  // Ensure current user is linked to the subscription in backend (always send)
  try {
    console.log('subscribeToPush: Sending subscription to backend for user linkage...');
    await apiRequest('/api/notifications/subscribe', {
      method: 'POST',
      body: JSON.stringify(subscription),
    });
    console.log('Push: Subscribed/Linked successfully');
  } catch (err) {
    console.warn('Push: Failed to link subscription to backend:', err.message);
  }

  return subscription;
}

/**
 * Convert base64 VAPID key to Uint8Array.
 * Web Push requiere la clave en formato "raw" (sin headers ASN.1).
 */
function urlBase64ToUint8Array(base64String) {
  console.log('urlBase64ToUint8Array: input length:', base64String.length);
  
  // Agregar padding si es necesario
  let base64 = base64String;
  while (base64.length % 4 !== 0) {
    base64 += '=';
  }
  
  // Reemplazar URL-safe characters
  base64 = base64.replace(/-/g, '+').replace(/_/g, '/');
  
  console.log('urlBase64ToUint8Array: after padding and replace, length:', base64.length);
  
  const rawData = window.atob(base64);
  console.log('urlBase64ToUint8Array: decoded length:', rawData.length);
  
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  
  console.log('urlBase64ToUint8Array: final array length:', outputArray.length);
  console.log('urlBase64ToUint8Array: first 10 bytes:', Array.from(outputArray.slice(0, 10)));
  
  return outputArray;
}

/**
 * Render breadcrumbs navigation.
 * @param {Array} paths - Array of {label, url} objects. url=null means current (no link).
 * @returns {string} HTML string for breadcrumbs
 */
function renderBreadcrumbs(paths) {
  if (!paths || !Array.isArray(paths) || paths.length === 0) {
    return '';
  }

  // Filter out null/undefined paths
  const validPaths = paths.filter(p => p && p.label);

  if (validPaths.length === 0) {
    return '';
  }

  let html = '<div class="text-sm text-gray-500 mb-4">';
  
  validPaths.forEach((path, index) => {
    const isLast = index === validPaths.length - 1;
    
    if (path.url && !isLast) {
      // Clickable link
      html += '<a href="' + path.url + '" class="text-blue-600 hover:text-blue-800">' + path.label + '</a>';
    } else {
      // Current page (no link)
      html += '<span class="text-gray-700">' + path.label + '</span>';
    }
    
    // Add separator except for last item
    if (!isLast) {
      html += '<span class="text-gray-400 mx-1">&gt;</span>';
    }
  });
  
  html += '</div>';
  return html;
}

/**
 * Render simple pagination: Anterior / N / Siguiente
 * Scrolls to top on page change
 * @param {string} containerId - ID of the container element
 * @param {number} currentPage - Current page (1-indexed)
 * @param {number} totalItems - Total number of items
 * @param {number} itemsPerPage - Items per page
 * @param {function} onPageChange - Callback when page changes: (page) => void
 */
function renderPagination(containerId, currentPage, totalItems, itemsPerPage, onPageChange) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const totalPages = Math.ceil(totalItems / itemsPerPage);
  if (totalPages <= 1) {
    container.innerHTML = '';
    return;
  }

  // Store callback globally
  window[`_pagination_${containerId}`] = (page) => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    onPageChange(page);
  };

  let html = `<div class="flex flex-wrap items-center justify-center gap-3 mt-6 pt-4 border-t">`;

  if (currentPage > 1) {
    html += `<button onclick="window._pagination_${containerId}(${currentPage - 1})" class="px-3 py-1 border rounded text-sm hover:bg-gray-100">← Anterior</button>`;
  }

  html += `<span class="px-3 py-1 text-sm font-medium">${currentPage} de ${totalPages}</span>`;

  if (currentPage < totalPages) {
    html += `<button onclick="window._pagination_${containerId}(${currentPage + 1})" class="px-3 py-1 border rounded text-sm hover:bg-gray-100">Siguiente →</button>`;
  }

  html += `</div>`;
  container.innerHTML = html;
}

// ============================================
// UI Component Library (SDD: ui-ux-improvements)
// ============================================

/**
 * Render skeleton loading placeholder with pulse animation
 * @param {Object} options - Component options
 * @param {string} options.type - 'card', 'list', or 'detail'
 * @param {number} options.count - Number of skeleton items (default: 1)
 * @returns {string} HTML string
 */
function renderSkeleton(options = {}) {
  const { type = 'card', count = 1 } = options;
  
  let items = '';
  for (let i = 0; i < count; i++) {
    if (type === 'card') {
      items += `
        <div class="skeleton-card skeleton-overlay">
          <div class="skeleton skeleton-title mb-2"></div>
          <div class="skeleton skeleton-text mb-1"></div>
          <div class="skeleton skeleton-text w-3/4"></div>
        </div>
      `;
    } else if (type === 'list') {
      items += `
        <div class="flex items-center gap-3 p-3 skeleton-overlay">
          <div class="skeleton skeleton-avatar"></div>
          <div class="flex-1">
            <div class="skeleton skeleton-title mb-1"></div>
            <div class="skeleton skeleton-text w-1/2"></div>
          </div>
        </div>
      `;
    } else if (type === 'detail') {
      items += `
        <div class="skeleton-card skeleton-overlay space-y-3">
          <div class="skeleton skeleton-title w-1/2"></div>
          <div class="skeleton skeleton-text"></div>
          <div class="skeleton skeleton-text"></div>
          <div class="skeleton skeleton-text w-3/4"></div>
          <div class="flex gap-2">
            <div class="skeleton w-20 h-8 rounded"></div>
            <div class="skeleton w-20 h-8 rounded"></div>
          </div>
        </div>
      `;
    }
  }
  
  return `<div class="skeleton-container space-y-4">${items}</div>`;
}

/**
 * Render empty state with emoji, title, subtitle, and optional CTA
 * @param {Object} options - Component options
 * @param {string} options.emoji - Emoji to display
 * @param {string} options.title - Main title
 * @param {string} options.subtitle - Subtitle/description
 * @param {Object} options.cta - Optional CTA button: {label, onClick}
 * @returns {string} HTML string
 */
function renderEmptyState(options = {}) {
  const { emoji = '📭', title = 'Sin contenido', subtitle = '', cta = null } = options;
  
  let ctaHtml = '';
  if (cta && cta.label) {
    const clickHandler = typeof cta.onClick === 'function' 
      ? `onclick="(${cta.onClick.toString()})()"` 
      : '';
    ctaHtml = `<button ${clickHandler} class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">${cta.label}</button>`;
  }
  
  return `
    <div class="text-center py-12">
      <div class="text-5xl mb-4">${emoji}</div>
      <h3 class="text-xl font-semibold text-gray-700 mb-2">${title}</h3>
      ${subtitle ? `<p class="text-gray-500 mb-4">${subtitle}</p>` : ''}
      ${ctaHtml}
    </div>
  `;
}

/**
 * Render reusable card component
 * @param {Object} options - Component options
 * @param {string} options.title - Card title
 * @param {string} options.content - Card content (truncated at 200 chars)
 * @param {Array} options.actions - Array of actions: [{label, onClick}]
 * @returns {string} HTML string
 */
function renderCard(options = {}) {
  const { title = '', content = '', actions = [] } = options;
  
  // Truncate content at 200 characters
  let displayContent = content;
  let showVerMas = false;
  if (content.length > 200) {
    displayContent = content.substring(0, 200) + '...';
    showVerMas = true;
  }
  
  let actionsHtml = '';
  if (actions && actions.length > 0) {
    actionsHtml = '<div class="flex flex-wrap gap-2 mt-3">';
    actions.forEach(action => {
      if (action && action.label) {
        const clickHandler = typeof action.onClick === 'function'
          ? `onclick="(${action.onClick.toString()})()"`
          : action.onClick || '';
        actionsHtml += `<button ${clickHandler} class="text-sm px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 transition">${action.label}</button>`;
      }
    });
    actionsHtml += '</div>';
  }
  
  return `
    <div class="bg-white rounded-lg shadow p-4 border border-gray-100">
      ${title ? `<h4 class="font-semibold text-gray-800 mb-2">${title}</h4>` : ''}
      <p class="text-gray-600">${displayContent}</p>
      ${showVerMas ? '<a href="#" class="text-blue-600 hover:text-blue-800 text-sm">Ver más</a>' : ''}
      ${actionsHtml}
    </div>
  `;
}

/**
 * Render standardized badge with variants
 * @param {Object} options - Component options
 * @param {string} options.text - Badge text
 * @param {string} options.variant - 'success', 'warning', 'error', or 'info'
 * @returns {string} HTML string
 */
function renderBadge(options = {}) {
  const { text = '', variant = 'info' } = options;
  
  // Map variant to CSS class, fallback to 'info' for unsupported
  const variantClass = (() => {
    switch (variant) {
      case 'success': return 'badge-success';
      case 'warning': return 'badge-warning';
      case 'error': return 'badge-error';
      default:
        if (variant !== 'info') {
          console.warn(`renderBadge: unsupported variant "${variant}", falling back to "info"`);
        }
        return 'badge-info';
    }
  })();
  
  return `<span class="badge ${variantClass}">${text}</span>`;
}

/**
 * Show toast notification (imperative - renders to DOM immediately)
 * @param {Object} options - Component options
 * @param {string} options.message - Toast message
 * @param {string} options.type - 'success', 'error', 'warning', or 'info'
 * @param {number} options.duration - Auto-dismiss duration in ms (default: 3000)
 */
function showToast(options = {}) {
  const { message = '', type = 'info', duration = 3000 } = options;
  
  // Get container or create one
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'fixed top-4 right-4 z-50 flex flex-col gap-2';
    document.body.appendChild(container);
  }
  
  // Type to color mapping
  const typeClasses = {
    success: 'bg-green-500 text-white',
    error: 'bg-red-500 text-white',
    warning: 'bg-yellow-500 text-white',
    info: 'bg-blue-500 text-white'
  };
  
  // Mobile detection for full-width styling
  const isMobile = window.innerWidth < 640;
  const widthClass = isMobile ? 'w-full left-0 right-0 top-0' : '';
  const baseClass = isMobile 
    ? `px-4 py-3 rounded-none shadow-lg ${typeClasses[type] || typeClasses.info}`
    : `px-6 py-3 rounded-lg shadow-lg ${typeClasses[type] || typeClasses.info}`;
  
  // Create toast element
  const toast = document.createElement('div');
  toast.className = `${baseClass} ${widthClass} flex items-center justify-between gap-3 min-w-[280px] animate-fade-in`;
  
  toast.innerHTML = `
    <span class="flex-1">${message}</span>
    <button onclick="this.parentElement.remove()" class="text-white hover:text-gray-200 font-bold text-lg leading-none">&times;</button>
  `;
  
  container.appendChild(toast);
  
  // Auto-dismiss timer
  setTimeout(() => {
    if (toast.parentElement) {
      toast.remove();
    }
  }, duration);
}

// ============================================
// Lazy Loading Utility (SDD: performance)
// ============================================

/**
 * LazyLoadingUtility - Manages lazy loading of images, maps, and scripts
 * Uses IntersectionObserver for efficient lazy loading
 */
class LazyLoadingUtility {
  constructor() {
    this.imageObserver = null;
    this.mapObserver = null;
    this.leafletLoaded = false;
    this.leafletLoading = false;
    this.leafletPromise = null;
    this.loadedImages = new WeakSet();
  }

  /**
   * Initialize all lazy loading observers
   */
  init() {
    // Initialize image observer
    if ('IntersectionObserver' in window) {
      this.imageObserver = new IntersectionObserver(
        (entries) => this._handleImageIntersection(entries),
        { rootMargin: '50px', threshold: 0.01 }
      );
    }

    // Initialize map observer
    if ('IntersectionObserver' in window) {
      this.mapObserver = new IntersectionObserver(
        (entries) => this._handleMapIntersection(entries),
        { rootMargin: '0px', threshold: 0.1 }
      );
    }

    // Observe existing lazy images
    this._observeExistingImages();

    // Observe existing lazy maps
    this._observeExistingMaps();

    console.log('LazyLoadingUtility initialized');
  }

  /**
   * Register an image element for lazy loading
   * @param {HTMLElement} img - Image element with data-src attribute
   */
  observeImage(img) {
    if (!img || !img.dataset.src || this.loadedImages.has(img)) return;

    if (this.imageObserver) {
      this.imageObserver.observe(img);
    } else {
      // Fallback: load immediately if no observer
      this._loadImage(img);
    }
  }

  /**
   * Register a map container for lazy loading
   * @param {string} containerId - ID of the map container element
   * @param {Object} options - {lat, lng, zoom, onReady callback}
   */
  observeMap(containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Store options for later use
    container.dataset.mapOptions = JSON.stringify(options);

    if (this.mapObserver) {
      this.mapObserver.observe(container);
    } else {
      // Fallback: load immediately if no observer
      this.loadLeaflet().then(() => this._initMap(container, options));
    }
  }

  /**
   * Load Leaflet scripts and CSS on demand
   * @returns {Promise} Resolves when Leaflet is ready
   */
  async loadLeaflet() {
    if (this.leafletLoaded) {
      return this.leafletPromise;
    }

    if (this.leafletLoading) {
      return this.leafletPromise;
    }

    this.leafletLoading = true;

    this.leafletPromise = new Promise(async (resolve, reject) => {
      try {
        // Check network condition
        const conn = navigator.connection;
        const isSlow = conn && (conn.effectiveType === '2g' || conn.effectiveType === 'slow-2g');

        if (isSlow) {
          console.log('LazyLoadingUtility: Skipping lazy load on slow network');
          reject(new Error('Slow network detected'));
          return;
        }

        // Load Leaflet CSS
        const cssLink = document.createElement('link');
        cssLink.rel = 'stylesheet';
        cssLink.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(cssLink);

        // Load MarkerCluster CSS
        const mcCssLink = document.createElement('link');
        mcCssLink.rel = 'stylesheet';
        mcCssLink.href = 'https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css';
        document.head.appendChild(mcCssLink);
        
        // Load MarkerCluster Default CSS
        const mcDefaultCssLink = document.createElement('link');
        mcDefaultCssLink.rel = 'stylesheet';
        mcDefaultCssLink.href = 'https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css';
        document.head.appendChild(mcDefaultCssLink);

        // Load Leaflet JS
        const jsScript = document.createElement('script');
        jsScript.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
        document.head.appendChild(jsScript);

        // Wait for script to load
        await new Promise((res, rej) => {
          jsScript.onload = res;
          jsScript.onerror = () => rej(new Error('Failed to load Leaflet'));
        });

        // Load MarkerCluster JS
        const mcScript = document.createElement('script');
        mcScript.src = 'https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js';
        document.head.appendChild(mcScript);

        await new Promise((res, rej) => {
          mcScript.onload = res;
          mcScript.onerror = () => rej(new Error('Failed to load MarkerCluster'));
        });

        this.leafletLoaded = true;
        this.leafletLoading = false;

        // Analytics tracking
        this._sendPerformanceEvent('lazy-map-loaded');

        console.log('LazyLoadingUtility: Leaflet loaded successfully');
        resolve(window.L);
      } catch (err) {
        this.leafletLoading = false;
        console.error('LazyLoadingUtility: Failed to load Leaflet:', err);
        reject(err);
      }
    });

    return this.leafletPromise;
  }

  /**
   * Cleanup all observers on page navigation
   */
  destroy() {
    if (this.imageObserver) {
      this.imageObserver.disconnect();
      this.imageObserver = null;
    }

    if (this.mapObserver) {
      this.mapObserver.disconnect();
      this.mapObserver = null;
    }

    this.loadedImages = new WeakSet();
    console.log('LazyLoadingUtility destroyed');
  }

  // ============================================
  // Private methods
  // ============================================

  _handleImageIntersection(entries) {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target;
        if (!this.loadedImages.has(img)) {
          this._loadImage(img);
        }
        // Unobserve after triggering
        if (this.imageObserver) {
          this.imageObserver.unobserve(img);
        }
      }
    });
  }

  _handleMapIntersection(entries) {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const container = entry.target;
        const options = JSON.parse(container.dataset.mapOptions || '{}');

        // Check if it's a click-triggered map (has user interacted)
        if (container.dataset.mapClicked === 'true') {
          this._initMapFromClick(container, options);
        }
        // Unobserve after triggering
        if (this.mapObserver) {
          this.mapObserver.unobserve(container);
        }
      }
    });
  }

  _loadImage(img) {
    if (!img || !img.dataset.src) return;

    this.loadedImages.add(img);
    img.dataset.loading = 'true';

    // Show loading state
    img.classList.add('lazy-image', 'lazy-image--loading');

    const tempImg = new Image();
    tempImg.onload = () => {
      img.src = img.dataset.src;
      img.removeAttribute('data-src');
      img.dataset.loaded = 'true';
      img.classList.remove('lazy-image--loading');
      img.classList.add('lazy-image--loaded');

      // Blur-up transition
      img.style.filter = 'blur(0)';
      img.style.opacity = '1';

      this._sendPerformanceEvent('lazy-image-loaded');
    };

    tempImg.onerror = () => {
      img.classList.remove('lazy-image--loading');
      img.classList.add('lazy-image--error');
      console.warn('LazyLoadingUtility: Failed to load image:', img.dataset.src);
    };

    tempImg.src = img.dataset.src;
  }

  async _initMap(container, options = {}) {
    try {
      const L = await this.loadLeaflet();

      const lat = options.lat || -32.862574;
      const lng = options.lng || -60.759585;
      const zoom = options.zoom || 12;

      // Initialize map
      const map = L.map(container.id).setView([lat, lng], zoom);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(map);

      container.dataset.mapInitialized = 'true';

      // Callback if provided
      if (options.onReady) {
        options.onReady(map, L);
      }

      return map;
    } catch (err) {
      console.error('LazyLoadingUtility: Failed to init map:', err);
    }
  }

  _initMapFromClick(container, options = {}) {
    const lat = options.lat || -32.862574;
    const lng = options.lng || -60.759585;

    // Show "Loading map..." indicator
    container.innerHTML = '<div class="map-loading">Cargando mapa...</div>';

    this._initMap(container, options);
  }

  _sendPerformanceEvent(eventType) {
    // Send to analytics if available
    if (typeof window.trackPerformanceEvent === 'function') {
      window.trackPerformanceEvent(eventType);
    }

    // Also dispatch custom event
    const event = new CustomEvent('lazy-loading', { detail: { eventType } });
    document.dispatchEvent(event);
  }

  _observeExistingImages() {
    const images = document.querySelectorAll('[data-src]');
    images.forEach(img => this.observeImage(img));
  }

  _observeExistingMaps() {
    const maps = document.querySelectorAll('[data-lazy-map]');
    maps.forEach(container => {
      const options = JSON.parse(container.dataset.mapOptions || '{}');
      this.observeMap(container.id, options);
    });
  }
}

// Create global instance
window.LazyLoadingUtility = new LazyLoadingUtility();
