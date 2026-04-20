# ADR-003: Autenticación con Cookies HttpOnly

## Fecha
2026-04-05

## Contexto
Se detectó riesgo de robo de JWT mediante ataques XSS al almacenar el token en `localStorage`.

## Decisión
Migrar el almacenamiento del JWT a cookies con los flags `HttpOnly`, `Secure` y `SameSite=Lax`.

## Consecuencias
- **Positivas**: Inmunidad a ataques XSS que intenten leer el token vía `document.cookie`. Mayor alineación con estándares de seguridad modernos.
- **Negativas**: Requiere un manejo más complejo en el Frontend para actualizar el estado de la UI cuando la cookie expira (vía chequeo en `/api/auth/me`).
