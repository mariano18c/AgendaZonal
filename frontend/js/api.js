const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://127.0.0.1:8000'
  : '';

// S-01/S-02: Escape HTML to prevent XSS
function escapeHtml(text) {
  if (text === null || text === undefined) return '';
  const div = document.createElement('div');
  div.textContent = String(text);
  return div.innerHTML;
}

function getToken() {
  return localStorage.getItem('token');
}

function setToken(token) {
  localStorage.setItem('token', token);
}

function removeToken() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
}

function getUser() {
  const user = localStorage.getItem('user');
  return user ? JSON.parse(user) : null;
}

function setUser(user) {
  localStorage.setItem('user', JSON.stringify(user));
}

function isLoggedIn() {
  return !!getToken();
}

async function apiRequest(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Error desconocido' }));
    throw new Error(error.detail || 'Error en la petición');
  }

  // B-03: Handle 204 No Content responses
  if (response.status === 204) {
    return null;
  }

  return response.json();
}

async function register(data) {
  const response = await apiRequest('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  setToken(response.token);
  setUser(response.user);
  return response;
}

async function login(usernameOrEmail, password) {
  const response = await apiRequest('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username_or_email: usernameOrEmail, password }),
  });
  setToken(response.token);
  setUser(response.user);
  return response;
}

function logout() {
  removeToken();
  window.location.href = '/';
}

async function getCategories() {
  return apiRequest('/api/categories');
}

async function getContacts(skip = 0, limit = 20) {
  return apiRequest(`/api/contacts?skip=${skip}&limit=${limit}`);
}

async function getContact(id) {
  return apiRequest(`/api/contacts/${id}`);
}

async function searchContacts(query, categoryId, skip = 0, limit = 20) {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  if (categoryId) params.set('category_id', categoryId);
  params.set('skip', skip);
  params.set('limit', limit);
  return apiRequest(`/api/contacts/search?${params.toString()}`);
}

async function searchContactsGeo(lat, lon, radiusKm, query, categoryId, skip = 0, limit = 20) {
  const params = new URLSearchParams();
  params.set('lat', lat);
  params.set('lon', lon);
  if (radiusKm) params.set('radius_km', radiusKm);
  if (query) params.set('q', query);
  if (categoryId) params.set('category_id', categoryId);
  params.set('skip', skip);
  params.set('limit', limit);
  return apiRequest(`/api/contacts/search?${params.toString()}`);
}

async function searchContactsByPhone(phone) {
  const params = new URLSearchParams();
  params.set('phone', phone);
  return apiRequest(`/api/contacts/search/phone?${params.toString()}`);
}

async function replyToReview(reviewId, replyText) {
  return apiRequest(`/api/reviews/${reviewId}/reply`, {
    method: 'POST',
    body: JSON.stringify({ reply_text: replyText }),
  });
}

async function createContact(data) {
  return apiRequest('/api/contacts', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

async function updateContact(id, data) {
  return apiRequest(`/api/contacts/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

async function deleteContact(id) {
  return apiRequest(`/api/contacts/${id}`, {
    method: 'DELETE',
  });
}

async function uploadContactImage(contactId, file) {
  const token = getToken();
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_URL}/api/contacts/${contactId}/image`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Error desconocido' }));
    throw new Error(error.detail || 'Error al subir la imagen');
  }

  return response.json();
}

async function deleteContactImage(contactId) {
  return apiRequest(`/api/contacts/${contactId}/image`, {
    method: 'DELETE',
  });
}

async function getContactHistory(contactId, skip = 0, limit = 20) {
  return apiRequest(`/api/contacts/${contactId}/history?skip=${skip}&limit=${limit}`);
}

async function verifyContact(contactId, isVerified) {
  return apiRequest(`/api/contacts/${contactId}/verify`, {
    method: 'POST',
    body: JSON.stringify({ is_verified: isVerified }),
  });
}

async function setVerificationLevel(contactId, level) {
  return apiRequest(`/api/admin/contacts/${contactId}/verification`, {
    method: 'PUT',
    body: JSON.stringify({ verification_level: level }),
  });
}

async function editContact(contactId, data) {
  return apiRequest(`/api/contacts/${contactId}/edit`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

async function getPendingContacts(skip = 0, limit = 20) {
  return apiRequest(`/api/contacts/pending?skip=${skip}&limit=${limit}`);
}

async function getContactChanges(contactId) {
  return apiRequest(`/api/contacts/${contactId}/changes`);
}

async function verifyContactChange(contactId, changeId) {
  return apiRequest(`/api/contacts/${contactId}/changes/${changeId}/verify`, {
    method: 'POST',
  });
}

async function rejectContactChange(contactId, changeId) {
  return apiRequest(`/api/contacts/${contactId}/changes/${changeId}/reject`, {
    method: 'POST',
  });
}

async function deleteContactChange(contactId, changeId) {
  return apiRequest(`/api/contacts/${contactId}/changes/${changeId}`, {
    method: 'DELETE',
  });
}

// User management API - with filters
async function getUsers(filter = 'all', role = '', username = '', skip = 0, limit = 20) {
  let params = `filter=${filter}&skip=${skip}&limit=${limit}`;
  if (role) params += `&role=${role}`;
  if (username) params += `&username=${encodeURIComponent(username)}`;
  return apiRequest(`/api/users?${params}`);
}

async function createUser(data) {
  return apiRequest('/api/users', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

async function updateUser(userId, data) {
  return apiRequest(`/api/users/${userId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

async function updateUserRole(userId, role) {
  return apiRequest(`/api/users/${userId}/role`, {
    method: 'PUT',
    body: JSON.stringify({ role }),
  });
}

async function deactivateUser(userId) {
  return apiRequest(`/api/users/${userId}`, {
    method: 'DELETE',
  });
}

async function activateUser(userId) {
  return apiRequest(`/api/users/${userId}/activate`, {
    method: 'POST',
  });
}

async function resetUserPassword(userId, newPassword) {
  return apiRequest(`/api/users/${userId}/reset-password`, {
    method: 'POST',
    body: JSON.stringify({ new_password: newPassword }),
  });
}

async function reportContact(contactId, reason, details) {
  return apiRequest(`/api/contacts/${contactId}/report`, {
    method: 'POST',
    body: JSON.stringify({ reason, details: details || null }),
  });
}

async function getCaptcha() {
  return apiRequest('/api/auth/captcha');
}

async function transferContactOwnership(contactId, newOwnerId) {
  return apiRequest(`/api/contacts/${contactId}/transfer-ownership`, {
    method: 'PUT',
    body: JSON.stringify({ new_owner_id: newOwnerId }),
  });
}

async function requestContactDeletion(contactId) {
  return apiRequest(`/api/contacts/${contactId}/request-deletion`, {
    method: 'POST',
  });
}

async function cancelContactDeletion(contactId) {
  return apiRequest(`/api/contacts/${contactId}/cancel-deletion`, {
    method: 'POST',
  });
}
