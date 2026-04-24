# Guía de Ingesta y Curación de Datos 🚀

Esta guía detalla el procedimiento para importar, validar y mantener actualizados los contactos en el ecosistema **AgendaZonal**.

## 📋 Flujo de Trabajo General

Para agregar nuevos datos, sigue estos pasos:

1.  **Preparacion**: Coloca los archivos fuente (VCF, ODS, TXT, Imagenes) en la carpeta raiz `./fuente_datos`.
2.  **Automatico (Watcher)**: Si el watcher esta corriendo, el pipeline se ejecuta solo.
3.  **Manual**: Corre los scripts correspondientes segun el tipo de archivo.
4.  **Moderacion**: Ejecuta el script de moderacion automatica para asignar categorias correctas.
5.  **Limpieza**: Los archivos procesados se mueven automaticamente a `./fuente_datos/importados_ok`.

> **Modo mas simple**: Dejar corriendo el watcher y solo soltar archivos en `./fuente_datos`.

---

## 🛠️ Scripts de Ingesta (`backend/scripts/`)

### 1. Ingesta de VCard y Texto (`data_curator_v2.py`)
Procesa archivos `.vcf` y exportaciones de chat de WhatsApp `.txt`.
- **Comando**: `python backend/scripts/data_curator_v2.py`
- **Función**: Extrae nombres, teléfonos y busca palabras clave en el contexto (ej. mensajes de chat) para adivinar la categoría.

### 2. Ingesta de Planillas ODS (`ingest_ods.py`)
Procesa archivos de LibreOffice Calc / OpenDocument.
- **Comando**: `python backend/scripts/ingest_ods.py`
- **Nota**: Asegúrate de que las columnas coincidan con el mapeo definido en el script (Nombre, Teléfono, Categoría).

### 3. Moderación Automática (`auto_moderate_v3.py`)
Mueve contactos de la categoría "Otro" a rubros específicos basados en palabras clave.
- **Comando**: `python backend/scripts/auto_moderate_v3.py`
- **Función**: Analiza nombres y descripciones buscando términos como "Plomero", "Remis", "Sanatorio", etc. Los que no puede clasificar permanecen en `pending`.

### 4. OCR de Imagenes (`ocr_engine.py`)
Extrae telefonos, nombres y categorias de imagenes (volantes, tarjetas, capturas de WhatsApp).
- **Comando manual**: `python backend/scripts/ocr_engine.py fuente_datos/imagen.jpg`
- **Comando batch**: `python backend/scripts/ocr_engine.py fuente_datos/imagenes/`
- **Requisito**: Tesseract OCR instalado (ver seccion Instalacion).
- **Fallback**: Si Tesseract no esta disponible, extrae info del nombre del archivo.
- **Salida**: Contactos persistidos como `pending` (confianza baja/media) o `active` (confianza alta).
- **Auditoria**: Resultados JSON en `backend/scripts/ocr_output/`.

### 5. Limpieza y Organizacion (`final_cleanup.py`)
Mueve los archivos ya procesados para mantener la carpeta de entrada limpia.
- **Comando**: `python backend/scripts/final_cleanup.py`
- **Resultado**: Los archivos pasan a `./fuente_datos/importados_ok`.

### 6. Watcher Automatico (`watcher.py`)
Demonio que monitorea `./fuente_datos` y ejecuta el pipeline automaticamente.
- **Comando**: `python backend/scripts/watcher.py`
- **Detener**: `Ctrl+C`
- **Log**: `backend/logs/watcher.log`
- **Flujo**: Detecta archivo nuevo -> debounce 3s -> router por extension -> moderacion automatica -> mover a importados_ok
- **Produccion (RPi)**: Copiar `docs/05-operations/watcher.service` a `/etc/systemd/system/` y habilitar con `systemctl enable`.

---

## 📏 Reglas de Oro (SSOT)

1.  **Teléfonos**: El formato estándar es **internacional completo**: `+549341XXXXXXX`.
    - Los scripts normalizan automáticamente la mayoría de los casos.
    - Si un número es corto (ej. 911, 147), se mantiene tal cual.
2.  **Categorías**: Evita dejar contactos en "Otro" (ID 26). Si el rubro no existe, agrégalo a la base de datos antes de importar.
3.  **Estado Pending**: Cualquier contacto con nombre ambiguo (ej. solo un nombre de pila) debe quedar en `status = 'pending'`.
4.  **Duplicados**: La lógica de persistencia utiliza el **teléfono** como clave única para evitar duplicados, actualizando la información existente si el número ya existe.

---

## Resolucion de Problemas

- **Errores de Unicode**: Si un archivo tiene emojis que fallan en Windows, los scripts ya manejan esto con `encoding='utf-8'`.
- **Base de Datos Bloqueada**: SQLite en modo WAL. Asegurate de cerrar conexiones en scripts (`conn.close()`).
- **OCR sin resultados**: Verificar que Tesseract este instalado: `tesseract --version`. Si no hay resultados, revisar el JSON de auditoria en `backend/scripts/ocr_output/`.

---

## Instalacion de Tesseract OCR

**Raspberry Pi / Linux (Debian)**:
```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-spa
```

**Windows**:
1. Descargar de: https://github.com/UB-Mannheim/tesseract/wiki
2. Instalar y agregar al PATH del sistema.
3. Verificar: `tesseract --version`

---

*Nota: Antes de una importacion masiva, realiza un backup de `backend/database/agenda.db`.*
