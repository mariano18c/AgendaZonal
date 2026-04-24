#!/usr/bin/env python3
"""
AgendaZonal - Data Watcher Daemon
==================================
Monitorea la carpeta ./fuente_datos y dispara automáticamente
el pipeline de ingesta cuando se detectan archivos nuevos.

Uso:
    python backend/scripts/watcher.py

Modo background (Linux/RPi):
    nohup python backend/scripts/watcher.py &

Servicio systemd:
    Ver: docs/05-operations/watcher.service
"""
import sys
import time
import logging
import subprocess
import shutil
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_DIR   = PROJECT_ROOT / "fuente_datos"
OK_DIR       = SOURCE_DIR / "importados_ok"
NO_OK_DIR    = SOURCE_DIR / "importados_no_ok"
SCRIPTS_DIR  = PROJECT_ROOT / "backend" / "scripts"
LOG_FILE     = PROJECT_ROOT / "backend" / "logs" / "watcher.log"

# ── Configuración de logging ───────────────────────────────────────────────────
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

_file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(_fmt)

# StreamHandler con encoding UTF-8 explícito para Windows
import io as _io
_stream_handler = logging.StreamHandler(
    _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    if hasattr(sys.stdout, 'buffer') else sys.stdout
)
_stream_handler.setFormatter(_fmt)

log = logging.getLogger("watcher")
log.setLevel(logging.INFO)
log.addHandler(_file_handler)
log.addHandler(_stream_handler)
log.propagate = False

# ── Extensiones soportadas ─────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {
    ".vcf", ".txt", ".ods", ".csv", ".jpg", ".jpeg", ".png"
}

# Carpetas a ignorar (para evitar loops al mover archivos procesados)
IGNORED_DIRS = {"importados_ok", "importados_no_ok", "vcf", "imagenes"}

# ── Debounce: esperar a que el archivo esté completo ───────────────────────────
# Algunos copiados de red o WhatsApp terminan en varios eventos.
# Esperamos DEBOUNCE_SECONDS sin actividad antes de procesar.
DEBOUNCE_SECONDS = 3
_pending: dict[str, threading.Timer] = {}
_pending_lock = threading.Lock()


# ── Runner de scripts ──────────────────────────────────────────────────────────

def run_script(script_name: str, env_vars: dict | None = None) -> bool:
    """Ejecuta un script Python del directorio de scripts. Devuelve True si éxito."""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        log.error(f"Script no encontrado: {script_path}")
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=120,  # 2 minutos máximo por script
        )
        if result.stdout:
            log.info(f"[{script_name}] {result.stdout.strip()}")
        if result.stderr:
            log.warning(f"[{script_name}] STDERR: {result.stderr.strip()}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log.error(f"[{script_name}] Timeout después de 120s")
        return False
    except Exception as e:
        log.error(f"[{script_name}] Error inesperado: {e}")
        return False


def move_file(src: Path, ok: bool):
    """Mueve un archivo procesado a la carpeta correspondiente."""
    dest_dir = OK_DIR if ok else NO_OK_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    # Si ya existe, sobreescribir
    if dest.exists():
        dest.unlink()
    try:
        shutil.move(str(src), str(dest))
        status = "OK" if ok else "NO_OK"
        log.info(f"Archivo movido [{status}]: {src.name} -> {dest_dir.name}/")
    except Exception as e:
        log.error(f"No se pudo mover {src.name}: {e}")


# ── Router de ingesta por tipo de archivo ─────────────────────────────────────

def process_vcf(filepath: Path) -> bool:
    """Procesa un archivo VCF individual moviéndolo a vcf/ y corriendo el curator."""
    vcf_dir = SOURCE_DIR / "vcf"
    vcf_dir.mkdir(parents=True, exist_ok=True)
    dest = vcf_dir / filepath.name
    if dest.exists():
        dest.unlink()
    shutil.move(str(filepath), str(vcf_dir))
    log.info(f"VCF movido a ./vcf/: {filepath.name}")

    # Correr el curador + persistencia
    ok = run_script("data_curator_v2.py")
    if ok:
        ok = run_script("persist_contacts.py")
    return ok


def process_text(filepath: Path) -> bool:
    """Procesa un archivo de texto (chat de WhatsApp, guía de contactos)."""
    # Mover al directorio raíz de fuente_datos con nombre estable si es chat
    log.info(f"Procesando texto: {filepath.name}")
    ok = run_script("data_curator_v2.py")
    if ok:
        ok = run_script("persist_contacts.py")
    return ok


def process_spreadsheet(filepath: Path) -> bool:
    """Procesa archivos ODS o CSV."""
    log.info(f"Procesando planilla: {filepath.name}")
    ok = run_script("ingest_ods.py")
    return ok


def process_image(filepath: Path) -> bool:
    """Procesa imágenes via OCR engine automático."""
    log.info(f"Procesando imagen via OCR: {filepath.name}")

    try:
        # Importar el motor OCR (mismo directorio)
        sys.path.insert(0, str(SCRIPTS_DIR))
        from ocr_engine import process_image_batch

        stats = process_image_batch([filepath])
        log.info(
            f"OCR resultado: {stats['persisted']} persistidos, "
            f"{stats['skipped']} sin datos, {stats['errors']} errores"
        )
        return stats["persisted"] > 0 or stats["skipped"] > 0

    except ImportError:
        log.error("No se pudo importar ocr_engine.py")
        return False
    except Exception as e:
        log.error(f"Error en OCR pipeline: {e}")
        return False


def ingest_file(filepath: Path):
    """Router principal: decide qué script ejecutar según la extensión."""
    ext = filepath.suffix.lower()
    log.info(f"[+] Iniciando ingesta: {filepath.name} (ext: {ext})")

    try:
        if ext == ".vcf":
            ok = process_vcf(filepath)
        elif ext == ".txt":
            ok = process_text(filepath)
        elif ext in (".ods", ".csv"):
            ok = process_spreadsheet(filepath)
        elif ext in (".jpg", ".jpeg", ".png"):
            ok = process_image(filepath)
        else:
            log.warning(f"Extensión no soportada: {ext}")
            ok = False

        # Después de cualquier ingesta exitosa, correr moderación automática
        if ok:
            log.info("Ejecutando moderacion automatica post-ingesta...")
            run_script("auto_moderate_v3.py")

        # Mover archivo a la carpeta correcta (si todavía existe en source_dir)
        if filepath.exists():
            move_file(filepath, ok)

        log.info(f"[{'OK' if ok else 'FAIL'}] Ingesta finalizada: {filepath.name}")

    except Exception as e:
        log.error(f"Error en ingest_file para {filepath.name}: {e}", exc_info=True)
        if filepath.exists():
            move_file(filepath, ok=False)


# ── Watchdog Handler ───────────────────────────────────────────────────────────

class IngestionHandler(FileSystemEventHandler):

    def _should_ignore(self, path: Path) -> bool:
        """Ignora carpetas de destino y archivos temporales."""
        parts = set(path.parts)
        for ignored in IGNORED_DIRS:
            if ignored in parts:
                return True
        # Ignorar archivos temporales del sistema
        if path.name.startswith(".") or path.name.endswith(".tmp"):
            return True
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return True
        return False

    def _schedule(self, path_str: str):
        """Registra (o reinicia) el timer debounce para un archivo."""
        with _pending_lock:
            # Cancelar timer previo si existe
            if path_str in _pending:
                _pending[path_str].cancel()

            filepath = Path(path_str)
            timer = threading.Timer(
                DEBOUNCE_SECONDS,
                self._trigger,
                args=[filepath]
            )
            _pending[path_str] = timer
            timer.start()

    def _trigger(self, filepath: Path):
        """Llamado cuando el debounce expiró: ejecuta la ingesta."""
        with _pending_lock:
            _pending.pop(str(filepath), None)

        if not filepath.exists():
            log.debug(f"Archivo ya no existe (quizás movido): {filepath.name}")
            return

        ingest_file(filepath)

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if self._should_ignore(path):
            return
        log.info(f"Nuevo archivo detectado: {path.name}")
        self._schedule(str(path))

    def on_moved(self, event):
        """También reaccionamos a movimientos (ej. copiar-pegar en Windows)."""
        if event.is_directory:
            return
        path = Path(event.dest_path)
        if self._should_ignore(path):
            return
        log.info(f"Archivo movido a la carpeta: {path.name}")
        self._schedule(str(path))


# ── Punto de entrada ───────────────────────────────────────────────────────────

def main():
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    OK_DIR.mkdir(parents=True, exist_ok=True)
    NO_OK_DIR.mkdir(parents=True, exist_ok=True)

    handler = IngestionHandler()
    observer = Observer()
    # recursive=True para detectar archivos en subcarpetas (excepto los ignorados)
    observer.schedule(handler, str(SOURCE_DIR), recursive=False)
    observer.start()

    log.info("=" * 60)
    log.info("AgendaZonal Data Watcher - INICIADO")
    log.info(f"Monitoreando : {SOURCE_DIR}")
    log.info(f"Log          : {LOG_FILE}")
    log.info(f"Debounce     : {DEBOUNCE_SECONDS}s")
    log.info("Extensiones  : " + ", ".join(sorted(SUPPORTED_EXTENSIONS)))
    log.info("Detener      : Ctrl+C")
    log.info("=" * 60)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Deteniendo watcher...")
        observer.stop()

    observer.join()
    log.info("Watcher finalizado.")


if __name__ == "__main__":
    main()
