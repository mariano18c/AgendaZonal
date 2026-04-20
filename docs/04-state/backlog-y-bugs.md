# Project Backlog & Known Issues

## Items Pendientes (Backlog)

### Alta Prioridad
- **Frontend UI for Reporting**: Implementar el modal de reporte de contacto en `profile.html`.
- **HSTS Enforcement**: Habilitar el header Strict-Transport-Security en producción (`main.py`).
- **User Dashboard Badges**: Mostrar contador de notificaciones no leídas vía `/api/notifications/unread-count`.

### Media Prioridad
- **vCard Export**: Implementar el endpoint `GET /api/contacts/{id}/export` para descargar ficha técnica.
- **Admin Unified Contacts UI**: Interfaz para gestionar contactos marcados como `flagged` o `suspended`.

---

## Bugs & Known Issues (Fixed or In-Progress)

1.  **VAPID Keys Template**: Falta un template genérico en `.env.example` para las llaves de Push.
2.  **Category Count Mismatch**: Los documentos mencionaban 24 categorías mientras que la DB tiene 26 (Agregados: "Cuidado de personas" y "Alquiler"). **(Fixed in docs)**.
3.  **Public Export visibility**: Riesgo de scraping en exportación masiva. **(Mitigado con Auth en ADR-004)**.

---

## Technical Debt
- **Refactor JS Modules**: Mover lógica de validación de formularios de los archivos HTML hacia `js/api.js` o un nuevo `js/forms.js`.
- **CSS Purge**: Asegurar que `output.css` esté realmente purgado para solo incluir clases usadas (RPi 5 Performance).