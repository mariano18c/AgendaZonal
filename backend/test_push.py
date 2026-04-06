#!/usr/bin/env python3
import sys
import logging
from app.database import SessionLocal
from app.routes.notifications import send_push_to_all

def main():
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        title = "Prueba AgendaZonal"
        body = "¡PWA Push Notifications habilitadas con éxito!"
        url = "/"
        
        print("Enviando Notificacion Push a todos los suscriptores...")
        count = send_push_to_all(db, title, body, url)
        print(f"OK: Se enviaron las notificaciones a {count} dispositivo(s).")
    except Exception as e:
        print(f"ERROR: Ocurrio un error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
