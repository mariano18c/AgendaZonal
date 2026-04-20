# ADR-001: SQLite sobre PostgreSQL

## Fecha
2026-03-15

## Contexto
Se requiere una plataforma altamente eficiente para correr en una Raspberry Pi 5 con 4GB de RAM. PostgreSQL consume ~600MB de base, lo cual es prohibitivo para el resto de los servicios en este hardware.

## Decisión
Usar **SQLite** operando en **WAL (Write-Ahead Logging) mode**.

## Consecuencias
- **Positivas**: Consumo de memoria base < 50MB. Latencia de lectura ultra-baja. Cero administración de procesos externos.
- **Negativas**: Limitación en concurrencia de escritura (manejable para un directorio local con < 50 req/s de escritura). No soporta tipos espaciales nativos sin extensiones.
