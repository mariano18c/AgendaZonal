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
    
    // Admin link
    if (user.role === 'admin') {
      adminLink = `<a href="/admin/users" class="text-gray-600 hover:text-gray-800">⚙️ Admin</a>`;
    }
    
    navbar.innerHTML = `
      <div class="flex items-center gap-4">
        <span class="text-gray-700">Hola, ${user.username}</span>
        ${pendingBadge}
        <a href="/add" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition">Agregar</a>
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
});
