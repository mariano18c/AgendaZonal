async function updateNavbar() {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;

  const isLoggedIn = !!localStorage.getItem('token');
  const user = JSON.parse(localStorage.getItem('user') || 'null');

  if (isLoggedIn && user) {
    // Check for pending changes
    let pendingBadge = '';
    let adminLink = '';
    
    try {
      const pending = await getPendingContacts();
      if (pending.length > 0) {
        const totalCount = pending.reduce((sum, c) => sum + c.pending_changes_count, 0);
        pendingBadge = `<a href="/pending" class="relative text-yellow-600 hover:text-yellow-800">
          ⏳ Pendientes
          <span class="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full px-1.5">${totalCount}</span>
        </a>`;
      }
    } catch (err) {
      // User doesn't have permission to see pending
    }
    
    // Admin/moderator links
    if (user.role === 'admin' || user.role === 'moderator') {
      adminLink = `
        <a href="/dashboard" class="text-gray-600 hover:text-gray-800">📊 Dashboard</a>
        <a href="/admin/reviews" class="text-gray-600 hover:text-gray-800">⭐ Reseñas</a>
        <a href="/admin/reports" class="text-gray-600 hover:text-gray-800">🚩 Reportes</a>
        <a href="/admin/analytics" class="text-gray-600 hover:text-gray-800">📊 Analytics</a>
        <a href="/admin/utilities" class="text-gray-600 hover:text-gray-800">🏥 Utilidades</a>
        ${user.role === 'admin' ? `<a href="/admin/users" class="text-gray-600 hover:text-gray-800">👥 Usuarios</a>` : ''}
      `;
    } else {
      adminLink = `<a href="/dashboard" class="text-gray-600 hover:text-gray-800">📊 Dashboard</a>`;
    }
    
    navbar.innerHTML = `
      <div class="flex items-center gap-4">
        <span class="text-gray-700">Hola, ${user.username}</span>
        ${pendingBadge}
        <a href="/contact-form?mode=add" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition">Agregar</a>
        ${adminLink}
        <button id="pwaInstallBtn" class="hidden text-green-600 hover:text-green-800" title="Instalar app">📲 Instalar</button>
        <button onclick="logout()" class="text-gray-600 hover:text-gray-800">Salir</button>
      </div>
    `;
  } else {
    navbar.innerHTML = `
      <div class="flex items-center gap-4">
        <a href="/login" class="text-blue-600 hover:text-blue-800">Iniciar sesión</a>
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

  // --- Push Notifications: auto-subscribe on login ---
  console.log('Push: Checking subscription. PushManager:', 'PushManager' in window, 'SW:', 'serviceWorker' in navigator, 'LoggedIn:', isLoggedIn());
  if ('PushManager' in window && 'serviceWorker' in navigator && isLoggedIn()) {
    console.log('Push: Will attempt subscription...');
    // Wait for service worker to be ready before subscribing
    navigator.serviceWorker.ready.then(reg => {
      console.log('Push: Service worker ready, attempting subscribe...');
      return subscribeToPush();
    }).then(sub => {
      console.log('Push: Subscription result:', sub ? 'SUCCESS' : 'FAILED');
    }).catch(err => {
      console.warn('Push: Subscription error:', err);
    });
  } else {
    console.log('Push: Skipped - not logged in or no push support');
  }
});

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

  // Check existing subscription
  let subscription = await reg.pushManager.getSubscription();
  console.log('subscribeToPush: Existing subscription:', subscription);

  if (!subscription) {
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
      console.log('subscribeToPush: convertedKey length:', convertedKey.length, '(should be 65 for P-256)');
      
      // Verificar los primeros bytes (debe empezar con 0x04 para P-256 uncompressed)
      console.log('subscribeToPush: first byte:', convertedKey[0], '(should be 4 for uncompressed point)');
      console.log('subscribeToPush: key bytes:', Array.from(convertedKey.slice(0, 8)));
      
      subscription = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: convertedKey,
      });
      console.log('subscribeToPush: Browser subscription created:', subscription);

      // Send subscription to backend
      console.log('subscribeToPush: Sending to backend...');
      await apiRequest('/api/notifications/subscribe', {
        method: 'POST',
        body: JSON.stringify(subscription),
      });
      console.log('Push: Subscribed successfully');
    } catch (err) {
      console.warn('Push: Subscription failed:', err.message);
      return null;
    }
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
