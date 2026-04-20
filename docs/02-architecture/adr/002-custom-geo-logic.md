# ADR-002: Lógica Geográfica Custom (Haversine)

## Fecha
2026-04-01

## Contexto
SQLite no posee extensiones espaciales (como SpatiaLite) disponibles de forma nativa en la mayoría de las distribuciones ligeras de Linux para RPi.

## Decisión
Implementar un filtrado en dos etapas:
1.  **Stage 1 (Pre-filter)**: `Bounding Box` mediante SQL simple (BETWEEN sobre lat/lon indexados).
2.  **Stage 2 (Refinement)**: Cálculo de `Haversine Formula` en Python puro sobre el subset resultante.

## Consecuencias
- **Positivas**: BÚsquedas de proximidad en milisegundos sin dependencias externas. Despliegue simplificado.
- **Negativas**: El rendimiento podría degradarse con > 50,000 registros (actualmente el proyecto tiene < 1,000).
