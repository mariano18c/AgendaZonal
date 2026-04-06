import logging
from app.database import SessionLocal
from app.routes.notifications import send_push_to_user
from app.models.user import User

logging.basicConfig(level=logging.INFO)
db = SessionLocal()

username = "mjc2"
try:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        print(f"Error: Usuario {username} no encontrado.")
    else:
        print(f"Enviando Notificacion Push a {username} (ID: {user.id})...")
        count = send_push_to_user(db, user.id, "Prueba Directa", "Si ves esto, las notificaciones funcionan.", "/profile")
        print(f"Resultado: {count} notificaciones enviadas exitosamente.")
except Exception as e:
    print(f"ERROR: {e}")
finally:
    db.close()
