# Project Brief: AgendaZonal

## Visión General
AgendaZonal es un directorio digital hiperlocal que conecta comercios y servicios con vecinos de la zona de Rosario/Ibarlucea, Argentina. Reemplaza las revistas publicitarias físicas con una plataforma PWA moderna, eficiente y offline-first.

## Stack Tecnológico (Gentle AI Stack)
- **Backend**: FastAPI (Python 3.11+), SQLite (WAL mode), SQLAlchemy ORM.
- **Frontend**: HTML5, Vanilla JS (Modular), Tailwind CSS (Compiled/PostCSS).
- **Security**: JWT (HttpOnly Cookies), Rate Limiting (SlowAPI), CSP, Secure Headers.
- **PWA**: Service Workers (Stale-while-revalidate), Manifest, Push Notifications (VAPID).
- **Geo**: Custom Haversine Logic + Bounding Box pre-filtering (No PostGIS/SpatiaLite).

## Hardware Constraints
- **Target**: Raspberry Pi 5 (4GB RAM).
- **Limitaciones**: 
    - RAM limitada (evitar dependencias pesadas como LLMs locales o Pandas).
    - SD I/O (máximo 2 workers de Uvicorn para evitar contención).
    - SQLite (alto rendimiento en lectura, limitado en escrituras concurrentes).

## Objetivo del Agente
Mantener la Agenda Zonal funcionando en hardware limitado sin sacrificar seguridad ni una estética premium.
- **Idioma Interfaz**: Español Rioplatense.
- **Zona Horaria**: America/Argentina/Buenos_Aires.