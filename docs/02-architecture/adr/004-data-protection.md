# ADR-004: Protección de Exfiltración (Data Scraping)

## Fecha
2026-04-10

## Contexto
Riesgo de scraping masivo de la base de datos comercial mediante los endpoints de exportación pública.

## Decisión
Restringir los endpoints `/api/contacts/export` y `/api/admin/analytics/export` exclusivamente a roles `admin` y `moderator`. Adicionalmente, implementar Rate Limiting estricto por IP.

## Consecuencias
- **Positivas**: Protección de la propiedad intelectual y de los datos de los clientes.
- **Negativas**: Los proveedores no pueden descargar sus propios datos masivamente de forma autónoma (deben solicitarlo a un admin).
