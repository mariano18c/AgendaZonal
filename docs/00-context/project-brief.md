# Project Brief: AgendaZonal

## Visión General
AgendaZonal es un directorio digital hiperlocal que conecta comercios y servicios con vecinos de la zona de Rosario/Ibarlucea, Argentina. Reemplaza las revistas publicitarias físicas con una plataforma PWA moderna, eficiente y offline-first.

## Stack Tecnológico (Gentle AI Stack)
- **Backend**: FastAPI (Python 3.11+), SQLite (WAL mode), SQLAlchemy ORM.
- **Frontend**: HTML5, Vanilla JS (Modular), Tailwind CSS (Compiled/PostCSS).
- **Security**: JWT (HttpOnly Cookies), Rate Limiting (SlowAPI), CSP, Secure Headers.
- **PWA**: Service Workers (Stale-while-revalidate), Manifest, Push Notifications (VAPID).
- **Geo**: Custom Haversine Logic + Bounding Box pre-filtering (No PostGIS/SpatiaLite).

## Hardware Constraints (Raspberry Pi 4/5)
- **CPU/RAM**: Optimización para 4GB RAM. Evitar procesos de fondo que consuman >10% CPU en idle.
- **I/O Storage**: MicroSD/SSD. Se debe minimizar el "Disk Thrashing". Logeo rotativo obligatorio.
- **Concurrency**: Máximo 2-4 workers de Uvicorn dependiendo del tráfico; monitoreo estricto de memoria.
- **SQLite Performance**: El uso de WAL mode es mandatorio para permitir lecturas mientras se escribe, pero se deben agrupar escrituras pesadas.

## Workflow SDD (Spec-Driven Development)
El proyecto se rige por un ciclo de vida asistido por IA:
1. **Spec**: Definición clara de requisitos técnicos.
2. **Design**: Diseño arquitectónico previo a la codificación.
3. **Apply**: Implementación atómica.
4. **Verify**: Testeo automático (Pytest/Playwright).
5. **Archive**: Documentación del cambio en el lifecycle. Cada vez que cierres esta tarea, usala para verificar y documentar las lecciones aprendidas.

## Objetivo del Agente
Mantener la Agenda Zonal funcionando en hardware limitado sin sacrificar seguridad ni una estética premium.
- **Idioma Interfaz**: Español Rioplatense.
- **Zona Horaria**: America/Argentina/Buenos_Aires.