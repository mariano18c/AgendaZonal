# Guía de Instalación y Configuración (Setup) 🛠️

Este documento describe los pasos necesarios para preparar el entorno de AgendaZonal, tanto en desarrollo como en producción (Raspberry Pi 5).

## 1. Requisitos del Sistema
- **Python**: 3.11 o superior.
- **Hardware**: Recomendado Raspberry Pi 5 (4GB RAM) para producción.
- **SO**: Linux (Debian/Raspberry Pi OS) o Windows (Desarrollo).

## 2. Instalación de Dependencias del Sistema

### Linux (Raspberry Pi 5)
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip sqlite3
# Dependencias para OCR
sudo apt install -y tesseract-ocr tesseract-ocr-spa
```

### Windows (Desarrollo)
1.  **Python**: Descargar e instalar desde [python.org](https://www.python.org/).
2.  **Tesseract OCR**:
    - Descargar instalador de [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).
    - Agregar el directorio de instalación (ej: `C:\Program Files\Tesseract-OCR`) al **PATH** del sistema.
    - Verificar con `tesseract --version`.

## 3. Configuración del Entorno Python

1.  **Clonar el repositorio**:
    ```bash
    git clone <url-del-repo>
    cd AgendaZonal_Anti
    ```

2.  **Crear y activar entorno virtual**:
    ```bash
    # Linux
    python3 -m venv .venv
    source .venv/bin/activate

    # Windows
    python -m venv .venv
    .venv\Scripts\activate
    ```

3.  **Instalar dependencias**:
    ```bash
    pip install -r backend/requirements.txt
    ```

## 4. Inicialización de la Base de Datos
El proyecto utiliza SQLite con modo WAL habilitado para alta concurrencia.
```bash
cd backend
python init_db.py
```
*Nota: Esto creará `backend/database/agenda.db` con el esquema inicial y las categorías base.*

## 5. Ejecución del Proyecto

### Backend (API)
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Watcher de Ingesta (Segundo Plano)
El watcher procesa automáticamente los archivos que caen en `./fuente_datos`.
```bash
# Ejecución directa
python backend/scripts/watcher.py

# En producción (Systemd)
sudo cp docs/05-operations/watcher.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable watcher.service
sudo systemctl start watcher.service
```

## 6. Verificación de la Instalación
- **API**: Abrir `http://localhost:8000/docs` para ver Swagger.
- **OCR**: Ejecutar `python backend/scripts/ocr_engine.py` para verificar disponibilidad de Tesseract.
- **Logs**: Revisar `backend/logs/watcher.log` para actividad del watcher.

---

> [!IMPORTANT]
> Asegúrate de que el archivo `.env` en la carpeta `backend` esté configurado correctamente (especialmente las claves JWT y variables de entorno).
