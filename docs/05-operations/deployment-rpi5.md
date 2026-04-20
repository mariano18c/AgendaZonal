# Despliegue en Raspberry Pi 5

Esta guía cubre la instalación completa de AgendaZonal en Raspberry Pi 5.

## Requisitos

- **Hardware**: Raspberry Pi 5 (4GB+ RAM recomendado)
- **OS**: Raspberry Pi OS (64-bit)
- **Almacenamiento**: SD card clase A2 o NVMe SSD
- **Red**: Conexión ethernet o WiFi configurado

## Preparación del Sistema

### 1. Actualizar SO
```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### 2. Instalar Python y dependencias
```bash
sudo apt install -y python3.11 python3.11-venv python3-pip git
pip3 install fastapi uvicorn gunicorn sqlalchemy pydantic python-jose python-multipart
```

### 3. Clonar proyecto
```bash
cd /opt
sudo git clone https://github.com/mariano18c/AgendaZonal.git
cd AgendaZonal
```

## Configuración

### 1. Variables de entorno
```bash
cp backend/.env.example backend/.env
# Editar .env con valores específicos
```

### 2.Permisos
```bash
sudo chown -R pi:pi /opt/AgendaZonal
```

### 3.SQLite WAL
El modo WAL está activo por defecto en la config:
```python
# app/database.py
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)
```

## Servidor

### Opción A: Gunicorn (Producción)
```bash
cd backend
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app \
  --bind 0.0.0.0:8000 \
  --log-file /var/log/agendazonal.log
```

### Opción B: Systemd Service
```ini
# /etc/systemd/system/agendazonal.service
[Unit]
Description=AgendaZonal
After=network.target

[Service]
User=pi
WorkingDirectory=/opt/AgendaZonal/backend
ExecStart=/usr/bin/python3 -m gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable agendazonal
sudo systemctl start agendazonal
```

## Proxy Inverso (Caddy)

### Instalación Caddy
```bash
curl -1s https://getcaddy.com | bash -s personal
```

### Configuración Caddyfile
```
agendazonal.example.com {
  reverse_proxy localhost:8000
  encode gzip
  log {
    output file /var/log/caddy/agendazonal.log
  }
}
```

```bash
sudo systemctl reload caddy
```

## Health Check

```bash
curl -f http://localhost:8000/api/health || echo "FAIL"
```

Expected response: `{"status":"ok"}`

## Backup y Restauración

### Backup
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp /opt/AgendaZonal/backend/data/agenda.db /opt/AgendaZonal/backend/data/agenda.db.$DATE.backup
```

### Restauración
```bash
cp /opt/AgendaZonal/backend/data/agenda.db.backup /opt/AgendaZonal/backend/data/agenda.db
```

## Monitoreo

### Ver logs
```bash
# Application
tail -f /var/log/agendazonal.log

# Systemd
journalctl -u agendazonal -f
```

### Resource usage
```bash
htop
df -h
```

## Actualización

```bash
cd /opt/AgendaZonal
git pull
sudo systemctl restart agendazonal
```