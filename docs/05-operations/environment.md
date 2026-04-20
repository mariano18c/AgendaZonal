# Environment Configuration: .env

Este archivo documenta las variables de entorno necesarias para correr AgendaZonal. El archivo `.env` debe ubicarse en la raíz del directorio `backend/`.

> [!WARNING]
> Nunca comitees el archivo `.env` al repositorio. Usar `.env.example` como plantilla.

---

## 1. Seguridad e Identidad

| Variable | Requerido | Valor Sugerido | Descripción |
|----------|-----------|----------------|-------------|
| `JWT_SECRET` | SI | (Random 64 chars) | Secreto para firmar tokens JWT. |
| `JWT_ALGORITHM` | SI | `HS256` | Algoritmo de encriptación. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | NO | `1440` | 24 horas por defecto. |

---

## 2. Base de Datos y Sistema

| Variable | Requerido | Valor Sugerido | Descripción |
|----------|-----------|----------------|-------------|
| `DATABASE_URL`| SI | `sqlite:///./app.db` | Ruta a la base SQLite. |
| `ENVIRONMENT` | SI | `production` | `production` o `development`. |
| `DEBUG` | NO | `False` | Activa logs detallados de FastAPI. |

---

## 3. Web Push (VAPID)

| Variable | Requerido | Descripción |
|----------|-----------|-------------|
| `VAPID_PUBLIC_KEY` | SI | Generada con `webpush-libs`. |
| `VAPID_PRIVATE_KEY`| SI | Guardar con extrema precaución. |
| `VAPID_ADMIN_EMAIL`| SI | Mail de contacto para los servicios de push (Google/Mozilla). |

---

## 4. Hardware & Server (RPi 5)

| Variable | Requerido | Valor Sugerido | Descripción |
|----------|-----------|----------------|-------------|
| `UVICORN_WORKERS` | NO | `2` | Máximo 4 para RPi 5 4GB. |
| `RATE_LIMIT_ENABLED` | NO | `True` | Habilita SlowAPI en endpoints críticos. |

---

## Mejores Prácticas
- **Secrets Management**: En la RPi 5, asegurate de que el archivo `.env` tenga permisos `600` (`chmod 600 .env`).
- **Backup**: Realizá copias de seguridad de las claves VAPID, ya que si se pierden, todos los navegadores suscriptos dejarán de recibir notificaciones.
