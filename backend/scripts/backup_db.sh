#!/bin/bash
# Script de Backup automatizado para AgendaZonal SQLite DB
# Diseñado para ejecutarse en Raspberry Pi 5 vía cron:
# 0 3 * * * cd /ruta/al/proyecto/backend/scripts && ./backup_db.sh

set -e

# Directorios
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DB_PATH="$DIR/../database/agenda.db"
BACKUP_DIR="$DIR/../backups"

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"

# Timestamp para el archivo
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_TMP="$BACKUP_DIR/agenda_backup_$TIMESTAMP.db"
BACKUP_FILE="$BACKUP_DIR/agenda_backup_$TIMESTAMP.db.gz"

echo "Iniciando backup de $DB_PATH..."

# Verificar si sqlite3 está instalado
if ! command -v sqlite3 &> /dev/null; then
    echo "ERROR: sqlite3 no está instalado. Instálalo con 'sudo apt-get install sqlite3'"
    exit 1
fi

# Hacer el backup usando el comando .backup nativo (seguro para WAL)
# Esto crea una copia en un paso sin bloquear escrituras durante lago tiempo.
sqlite3 "$DB_PATH" ".backup '$BACKUP_TMP'"

echo "Backup creado: $BACKUP_TMP"
echo "Comprimiendo..."

# Comprimir la copia
gzip "$BACKUP_TMP"

echo "Backup comprimido exitosamente: $BACKUP_FILE"

# Opcional: Eliminar backups más antiguos a 7 días
# Descomentar la siguiente línea para activar la rotación:
find "$BACKUP_DIR" -name "agenda_backup_*.db.gz" -type f -mtime +7 -exec rm {} \;
echo "Limpieza de backups antiguos (más de 7 días) completada."

echo "Proceso finalizado!"
exit 0
