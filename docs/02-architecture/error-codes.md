# Error Codes Catalog

Este documento cataloga los códigos de error HTTP used en el backend.

## HTTP Status Codes

| Code | Meaning | Common Cause |
|------|--------|-----------|
| 400 | Bad Request | Datos inválidos, validaciones fallidas |
| 401 | Unauthorized | Credenciales inválidas |
| 403 | Forbidden | Permisos insuficientes |
| 404 | Not Found | Recurso no existe |
| 409 | Conflict | Recurso duplicado |
| 500 | Internal Error | Error del servidor |

## Error Messages by Category

### Auth (auth.py)
- `"Email o username ya registrado"` — Intento de registro con datos existentes
- `"Credenciales inválidas"` — Login con credenciales wrong
- `"Cuenta pendiente de aprobación"` — Usuario esperando approval
- `"Usuario desactivado"` — Cuenta deshabilitada

### Contacts (contacts.py)
- `"Contacto no encontrado"` — ID no existe
- `"No tiene permisos para editar/ver/eliminar"` — Ownership check failed
- `"Solo el usuario que sugirió el cambio puede eliminarlo"` — Permission denied
- `"Coordenadas inválidas"` — Formato GPS incorrecto
- `"Solo se permiten archivos JPG"` — File type wrong
- `"El archivo es demasiado grande (máximo 5MB)"` — Size limit exceeded
- `"Máximo 5 fotos por contacto"` — Limit exceeded

### Admin (admin.py)
- `"Requiere rol de moderador o admin"` — RBAC check failed
- `"Reporte no encontrado"` — Report ID wrong
- `"Utilidad no encontrada"` — Utility not found
- `"No puedes reportar tu propio contacto"` — Self-report attempt
- `"Ya has reportado este contacto"` — Duplicate report
- `"No tiene permisos para exportar datos"` — Permission denied

### Users (users.py)
- `"Acceso denegado. Se requiere rol de administrador"` — RBAC failed
- `"Usuario no encontrado"` — User ID wrong
- `"Rol inválido. Valores permitidos: admin, moderator, user"` — Invalid role
- `"No se puede cambiar el rol de unadmin"` — Cannot demote self
- `"Email ya registrado"` — Duplicate email
- `"Username ya registrado"` — Duplicate username

### Notifications (notifications.py)
- `"Push notifications not configured"` — VAPID keys missing
- `"Missing keys: p256dh and auth required"` — Subscription incomplete
- `"Notificación no encontrada"` — ID wrong

## Best Practices

1. **Mensajes localizeados**: El frontend debe internacionalizar estos mensajes
2. **Logging**: Errores 500 deben logged con traceback completo
3. **Security**: No exponer detalles internos en errores 500