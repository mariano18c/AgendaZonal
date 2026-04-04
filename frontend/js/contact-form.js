/**
 * Unified Contact Form Component for AgendaZonal.
 * 
 * Operates in two modes:
 * - Add mode: ?mode=add (or no params) — creates new contacts
 * - Edit mode: ?id=X — modifies existing contacts
 * 
 * Handles: mode detection, field population, permissions,
 * form submission, photo/gallery, schedule toggle, Leaflet map.
 */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let formMode = 'add';
let contactId = null;
let contact = null;
let user = null;
let isOwner = false;
let isModeratorOrAdmin = false;
let selectedPhoto = null;
let selectedGalleryFiles = [];
let editMapInstance = null;

// ---------------------------------------------------------------------------
// Mode Detection (Task 2.2)
// ---------------------------------------------------------------------------

/**
 * Detect form mode from URL query parameters.
 * @returns {{ mode: 'add'|'edit', contactId: string|null }}
 */
function detectFormMode() {
  const params = new URLSearchParams(window.location.search);
  const id = params.get('id');
  const mode = params.get('mode');

  if (id) return { mode: 'edit', contactId: id };
  if (mode === 'add') return { mode: 'add', contactId: null };
  return { mode: 'add', contactId: null }; // default
}

// ---------------------------------------------------------------------------
// Category Emoji Map
// ---------------------------------------------------------------------------

function getCategoryEmoji(code) {
  const emojis = {
    100: '🔧', 101: '🔥', 102: '⚡', 103: '✂️', 104: '🧱',
    105: '🖌️', 106: '🪚', 107: '🛒', 108: '🥩', 109: '🥬',
    110: '🥖', 111: '👕', 112: '💊', 113: '📚', 114: '🍺',
    115: '🍽️', 116: '🎶', 117: '🎁', 118: '🐾', 119: '🔩',
    120: '🏪', 121: '🧸', 122: '📦', 123: '❤️', 124: '🏠',
    999: '📌'
  };
  return emojis[code] || '📌';
}

// ---------------------------------------------------------------------------
// Load Categories
// ---------------------------------------------------------------------------

async function loadCategories() {
  try {
    const categories = await getCategories();
    const select = document.getElementById('category');
    categories.forEach(cat => {
      const option = document.createElement('option');
      option.value = cat.id;
      option.textContent = `${getCategoryEmoji(cat.code)} ${cat.name}`;
      select.appendChild(option);
    });
  } catch (err) {
    console.error('Error loading categories:', err);
  }
}

// ---------------------------------------------------------------------------
// Load Contact Data (Task 2.3)
// ---------------------------------------------------------------------------

async function loadContactData(id) {
  if (!id) return;

  document.getElementById('loadingMsg').classList.remove('hidden');

  try {
    contact = await getContact(id);
    user = getUser();

    if (user) {
      isOwner = user.id === contact.user_id;
      isModeratorOrAdmin = user.role === 'moderator' || user.role === 'admin';
    }

    // Update title
    document.getElementById('formTitle').textContent = `Editar: ${contact.name}`;
    document.getElementById('submitBtn').textContent = 'Guardar Cambios';

    // Update breadcrumbs
    const breadcrumbsData = [
      { label: 'Inicio', url: '/' },
      { label: contact.name, url: `/profile?id=${id}` },
      { label: 'Editar', url: null }
    ];
    document.getElementById('breadcrumbs').innerHTML = renderBreadcrumbs(breadcrumbsData);

    // Show permission info
    const permInfo = document.getElementById('permissionInfo');
    if (isOwner || isModeratorOrAdmin) {
      permInfo.textContent = '👤 Podés editar todos los campos. Los cambios se aplicarán inmediatamente.';
    } else if (user) {
      permInfo.textContent = '💡 Podés editar solo los campos vacíos. Los cambios requerirán verificación.';
    } else {
      permInfo.textContent = '🔒 Iniciá sesión para editar. Podés sugerir cambios para los campos vacíos.';
    }
    permInfo.classList.remove('hidden');

    // Show info badges
    showInfoBadges();

    // Load categories and populate form
    await loadCategories();
    populateForm();

    // Load gallery for owner/admin
    if (isOwner || isModeratorOrAdmin) {
      await loadGallery();
    }

    // Init map if coordinates exist
    if (contact.latitude && contact.longitude) {
      initMapWithCoords(contact.latitude, contact.longitude);
    }

    document.getElementById('loadingMsg').classList.add('hidden');
    document.getElementById('contactForm').classList.remove('hidden');
  } catch (err) {
    document.getElementById('loadingMsg').innerHTML = `<p class="text-red-500">Error: ${err.message}</p>`;
  }
}

function showInfoBadges() {
  const badges = [];
  if (contact.is_verified) {
    badges.push('<span class="px-3 py-1 bg-green-100 text-green-700 text-sm rounded-full">✓ Verificado</span>');
  }
  if (contact.avg_rating && contact.avg_rating > 0) {
    badges.push(`<span class="px-3 py-1 bg-yellow-100 text-yellow-700 text-sm rounded-full">⭐ ${contact.avg_rating.toFixed(1)} (${contact.review_count || 0} reseñas)</span>`);
  }
  if (contact.pending_changes_count > 0) {
    badges.push(`<span class="px-3 py-1 bg-orange-100 text-orange-700 text-sm rounded-full">⏳ ${contact.pending_changes_count} cambio(s) pendiente(s)</span>`);
  }

  if (badges.length > 0) {
    document.getElementById('infoBadges').innerHTML = badges.join('');
    document.getElementById('infoBadges').classList.remove('hidden');
  }
}

function populateForm() {
  const fields = ['name', 'phone', 'email', 'address', 'city', 'neighborhood',
    'description', 'about', 'schedule', 'website', 'maps_url',
    'latitude', 'longitude', 'instagram', 'facebook'];

  fields.forEach(field => {
    const input = document.getElementById(field);
    if (input && contact[field] !== undefined) {
      input.value = contact[field] || '';

      if (!canEditField(field)) {
        input.disabled = true;
        input.classList.add('bg-gray-100', 'text-gray-500');
      }
    }
  });

  // Category
  const categorySelect = document.getElementById('category');
  if (contact.category_id) {
    categorySelect.value = contact.category_id;
  }
  if (!canEditField('category_id')) {
    categorySelect.disabled = true;
    categorySelect.classList.add('bg-gray-100', 'text-gray-500');
  }

  // Current photo
  if (contact.photo_path) {
    document.getElementById('currentPhotoImg').src = contact.photo_path;
    document.getElementById('currentPhoto').classList.remove('hidden');
    if (isOwner || isModeratorOrAdmin) {
      document.getElementById('deleteCurrentPhotoBtn').classList.remove('hidden');
    }
  }

  // Photo/gallery sections - only for owner/moderator in edit mode
  if (formMode === 'edit' && !isOwner && !isModeratorOrAdmin) {
    document.getElementById('photoSection').classList.add('hidden');
    document.getElementById('gallerySection').classList.add('hidden');
  }

  // Load structured schedules
  loadSchedules();
}

// ---------------------------------------------------------------------------
// Permissions (Task 2.4)
// ---------------------------------------------------------------------------

function canEditField(fieldName) {
  if (formMode === 'add') return true;
  if (isOwner || isModeratorOrAdmin) return true;
  const value = contact[fieldName];
  return value === null || value === undefined || value === '';
}

// ---------------------------------------------------------------------------
// Map Handling (Task 2.8)
// ---------------------------------------------------------------------------

function initMapWithCoords(lat, lng) {
  const result = initEditMap('map', lat, lng);
  editMapInstance = result;
}

async function getMyLocation() {
  const btn = document.getElementById('geoBtn');
  const status = document.getElementById('geoStatus');
  btn.disabled = true;
  btn.textContent = '⏳ Obteniendo...';

  try {
    const pos = await getUserLocation();
    document.getElementById('latitude').value = pos.lat;
    document.getElementById('longitude').value = pos.lon;
    status.textContent = '✅ Ubicación obtenida';

    // Update or create map
    if (editMapInstance && editMapInstance.marker) {
      editMapInstance.marker.setLatLng([pos.lat, pos.lon]);
      if (editMapInstance.map) {
        editMapInstance.map.setView([pos.lat, pos.lon], 15);
      }
    } else {
      initMapWithCoords(pos.lat, pos.lon);
    }
  } catch (err) {
    status.textContent = '❌ ' + err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = '📍 Obtener mi ubicación';
  }
}

// ---------------------------------------------------------------------------
// Schedule Toggle (Task 2.7)
// ---------------------------------------------------------------------------

function toggleScheduleMode() {
  const toggle = document.getElementById('scheduleModeToggle');
  const textMode = document.getElementById('scheduleTextMode');
  const gridMode = document.getElementById('scheduleGrid');

  if (toggle.checked) {
    textMode.classList.add('hidden');
    gridMode.classList.remove('hidden');
  } else {
    textMode.classList.remove('hidden');
    gridMode.classList.add('hidden');
  }
}

async function loadSchedules() {
  if (!contactId) return;
  try {
    const schedules = await apiRequest(`/api/contacts/${contactId}/schedules`);

    if (schedules.length > 0) {
      // Auto-enable the toggle if structured schedules exist
      document.getElementById('scheduleModeToggle').checked = true;
      toggleScheduleMode();

      const dayMap = { 0: 'sun', 1: 'mon', 2: 'tue', 3: 'wed', 4: 'thu', 5: 'fri', 6: 'sat' };

      schedules.forEach(s => {
        const dayKey = dayMap[s.day_of_week];
        if (dayKey) {
          const openInput = document.getElementById(`schedule_${dayKey}_open`);
          const closeInput = document.getElementById(`schedule_${dayKey}_close`);
          if (openInput && s.open_time) openInput.value = s.open_time.substring(0, 5);
          if (closeInput && s.close_time) closeInput.value = s.close_time.substring(0, 5);
        }
      });
    }
  } catch (err) {
    console.log('No structured schedules found');
  }
}

function getStructuredSchedules() {
  const toggle = document.getElementById('scheduleModeToggle');
  if (!toggle || !toggle.checked) return [];

  const days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
  const schedules = [];

  days.forEach((day, index) => {
    const openInput = document.getElementById(`schedule_${day}_open`);
    const closeInput = document.getElementById(`schedule_${day}_close`);

    if (openInput && closeInput && openInput.value && closeInput.value) {
      schedules.push({
        day_of_week: index + 1, // Monday = 1
        open_time: openInput.value + ':00',
        close_time: closeInput.value + ':00'
      });
    }
  });

  return schedules;
}

// ---------------------------------------------------------------------------
// Photo / Gallery Handling (Task 2.6)
// ---------------------------------------------------------------------------

async function loadGallery() {
  if (!isOwner && !isModeratorOrAdmin) return;

  try {
    const photos = await apiRequest(`/api/contacts/${contactId}/photos`);
    const galleryDiv = document.getElementById('existingGallery');

    if (photos.length > 0) {
      const cacheBuster = Date.now();
      galleryDiv.innerHTML = photos.map(p => `
        <div class="gallery-item">
          <img src="${escapeHtml(p.photo_path)}?t=${cacheBuster}" alt="Foto" onclick="window.open('${escapeHtml(p.photo_path)}?t=${cacheBuster}', '_blank')">
          <button type="button" class="delete-btn" onclick="deleteGalleryPhoto(${p.id})" title="Eliminar">×</button>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error('Error loading gallery:', err);
  }
}

async function deleteGalleryPhoto(photoId) {
  if (!confirm('¿Eliminar esta foto?')) return;
  try {
    await apiRequest(`/api/contacts/${contactId}/photos/${photoId}`, { method: 'DELETE' });
    await loadGallery();
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

// Photo input handler
document.getElementById('photo').addEventListener('change', function (e) {
  const file = e.target.files[0];
  if (file) {
    if (!file.type.includes('jpeg')) {
      showAlert('Solo se permiten imágenes JPEG', 'error');
      this.value = '';
      return;
    }
    selectedPhoto = file;
    const reader = new FileReader();
    reader.onload = (e) => {
      document.getElementById('photoPreviewImg').src = e.target.result;
      document.getElementById('photoPreview').classList.remove('hidden');
      if (contact && contact.photo_path) {
        document.getElementById('currentPhoto').classList.add('hidden');
      }
    };
    reader.readAsDataURL(file);
  }
});

function removePhoto() {
  selectedPhoto = null;
  document.getElementById('photo').value = '';
  document.getElementById('photoPreview').classList.add('hidden');
  if (contact && contact.photo_path) {
    document.getElementById('currentPhotoImg').src = contact.photo_path;
    document.getElementById('currentPhoto').classList.remove('hidden');
  }
}

async function deleteCurrentPhoto() {
  if (!confirm('¿Eliminar la foto actual?')) return;
  try {
    await deleteContactImage(contactId);
    contact.photo_path = null;
    document.getElementById('currentPhoto').classList.add('hidden');
    document.getElementById('deleteCurrentPhotoBtn').classList.add('hidden');
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

// Gallery file handler
document.getElementById('galleryFiles').addEventListener('change', function (e) {
  const files = Array.from(e.target.files);
  const maxNew = 5 - selectedGalleryFiles.length;
  selectedGalleryFiles = selectedGalleryFiles.concat(files.slice(0, maxNew));

  const preview = document.getElementById('galleryPreview');
  preview.innerHTML = selectedGalleryFiles.map((f, i) => `
    <div class="gallery-item">
      <img src="" data-index="${i}" class="preview-img">
      <button type="button" class="delete-btn" onclick="removeGalleryFile(${i})">×</button>
    </div>
  `).join('');

  selectedGalleryFiles.forEach((f, i) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = document.querySelector(`[data-index="${i}"]`);
      if (img) img.src = e.target.result;
    };
    reader.readAsDataURL(f);
  });
});

function removeGalleryFile(index) {
  selectedGalleryFiles.splice(index, 1);
  const preview = document.getElementById('galleryPreview');
  preview.innerHTML = selectedGalleryFiles.map((f, i) => `
    <div class="gallery-item">
      <img src="" data-index="${i}" class="preview-img">
      <button type="button" class="delete-btn" onclick="removeGalleryFile(${i})">×</button>
    </div>
  `).join('');

  selectedGalleryFiles.forEach((f, i) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = document.querySelector(`[data-index="${i}"]`);
      if (img) img.src = e.target.result;
    };
    reader.readAsDataURL(f);
  });
}

async function uploadGalleryPhoto(id, file) {
  const formData = new FormData();
  formData.append('file', file);
  const token = getToken();
  await fetch(`/api/contacts/${id}/photos`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
  });
}

// ---------------------------------------------------------------------------
// Form Submission (Task 2.5)
// ---------------------------------------------------------------------------

document.getElementById('contactForm').addEventListener('submit', async (e) => {
  e.preventDefault();

  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = 'Guardando...';

  // Build data object
  const data = {};
  const fields = ['name', 'phone', 'email', 'address', 'city', 'neighborhood',
    'description', 'about', 'schedule', 'website', 'maps_url',
    'instagram', 'facebook'];

  fields.forEach(field => {
    const input = document.getElementById(field);
    if (input && !input.disabled) {
      const val = input.value.trim();
      if (val) {
        data[field] = val;
      } else if (formMode === 'add') {
        // In add mode, send null for empty optional fields
        if (field !== 'name' && field !== 'phone') {
          data[field] = null;
        }
      }
    }
  });

  // Category
  const categorySelect = document.getElementById('category');
  if (!categorySelect.disabled && categorySelect.value) {
    data.category_id = parseInt(categorySelect.value);
  }

  // Coordinates
  const lat = document.getElementById('latitude');
  const lng = document.getElementById('longitude');
  if (lat.value) data.latitude = parseFloat(lat.value);
  if (lng.value) data.longitude = parseFloat(lng.value);

  try {
    let result;

    if (formMode === 'add') {
      // CREATE: POST /api/contacts
      result = await createContact(data);

      // Upload photo if selected
      if (selectedPhoto) {
        await uploadContactImage(result.id, selectedPhoto);
      }

      // Upload gallery photos
      for (const file of selectedGalleryFiles) {
        await uploadGalleryPhoto(result.id, file);
      }

      // Save structured schedules
      const schedules = getStructuredSchedules();
      if (schedules.length > 0) {
        await apiRequest(`/api/contacts/${result.id}/schedules`, {
          method: 'PUT',
          body: JSON.stringify(schedules)
        });
      }

      // Show success (add mode)
      document.getElementById('contactForm').classList.add('hidden');
      document.getElementById('successAdd').classList.remove('hidden');

    } else {
      // UPDATE: PUT /api/contacts/{id} or pending changes
      if (isOwner || isModeratorOrAdmin) {
        result = await updateContact(contactId, data);
        document.getElementById('successMsg').textContent = '✅ Cambios guardados exitosamente';
      } else {
        result = await editContact(contactId, data);
        document.getElementById('successMsg').textContent = '✅ Cambios enviados. Pendientes de verificación.';
      }
      document.getElementById('successMsg').classList.remove('hidden');
      document.getElementById('errorMsg').classList.add('hidden');

      // Upload new photo if selected (owner/admin only)
      if (selectedPhoto && (isOwner || isModeratorOrAdmin)) {
        await uploadContactImage(contactId, selectedPhoto);
      }

      // Upload gallery photos
      for (const file of selectedGalleryFiles) {
        await uploadGalleryPhoto(contactId, file);
      }

      // Save structured schedules (owner/admin only)
      if (isOwner || isModeratorOrAdmin) {
        const schedules = getStructuredSchedules();
        if (schedules.length > 0) {
          await apiRequest(`/api/contacts/${contactId}/schedules`, {
            method: 'PUT',
            body: JSON.stringify(schedules)
          });
        }
      }

      // Reload to reflect changes
      setTimeout(() => window.location.reload(), 1500);
    }
  } catch (err) {
    document.getElementById('errorMsg').textContent = err.message;
    document.getElementById('errorMsg').classList.remove('hidden');
    document.getElementById('successMsg').classList.add('hidden');
  } finally {
    btn.disabled = false;
    btn.textContent = formMode === 'add' ? 'Guardar Contacto' : 'Guardar Cambios';
  }
});

function resetToAdd() {
  document.getElementById('successAdd').classList.add('hidden');
  document.getElementById('contactForm').classList.remove('hidden');
  document.getElementById('contactForm').reset();
  document.getElementById('errorMsg').classList.add('hidden');
  document.getElementById('successMsg').classList.add('hidden');

  // Reset photo state
  selectedPhoto = null;
  selectedGalleryFiles = [];
  document.getElementById('photoPreview').classList.add('hidden');
  document.getElementById('galleryPreview').innerHTML = '';
  document.getElementById('existingGallery').innerHTML = '';

  // Reset map
  if (editMapInstance && editMapInstance.map) {
    editMapInstance.map.remove();
    editMapInstance = null;
  }
  document.getElementById('map').classList.add('hidden');
}

// ---------------------------------------------------------------------------
// Initialization
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', async () => {
  const detected = detectFormMode();
  formMode = detected.mode;
  contactId = detected.contactId;

  // Check authentication
  if (!isLoggedIn()) {
    document.getElementById('loginRequired').classList.remove('hidden');
    document.getElementById('contactForm').classList.add('hidden');
    return;
  }

  if (formMode === 'edit' && contactId) {
    // Edit mode: load contact data
    await loadContactData(contactId);
  } else {
    // Add mode: initialize empty form
    document.getElementById('formTitle').textContent = 'Agregar Contacto';
    document.getElementById('submitBtn').textContent = 'Guardar Contacto';
    document.getElementById('contactForm').classList.remove('hidden');
    await loadCategories();

    // Initialize empty map
    const mapDiv = document.getElementById('map');
    mapDiv.classList.remove('hidden');
    editMapInstance = initEditMap('map', null, null);
  }
});
