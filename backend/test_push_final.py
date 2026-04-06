import logging
import json
from app.database import SessionLocal
from app.models.push_subscription import PushSubscription
from app.routes.notifications import VAPID_PRIVATE_KEY, VAPID_CLAIM_EMAIL
from pywebpush import webpush, WebPushException

logging.basicConfig(level=logging.INFO)
db = SessionLocal()

try:
    # Get the latest subscription
    sub = db.query(PushSubscription).order_by(PushSubscription.id.desc()).first()
    if not sub:
        print("Error: No hay suscripciones.")
    else:
        print(f"Probando envio a ID {sub.id}, Endpoint: {sub.endpoint[:50]}...")
        payload = json.dumps({
            "title": "¡Prueba Final!",
            "body": f"Si ves esto, la suscripcion {sub.id} esta activa.",
            "url": "/"
        })
        
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth}
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIM_EMAIL}
            )
            print(f"EXITO: El servidor de push acepto la notificacion para ID {sub.id}.")
        except WebPushException as e:
            print(f"FALLO: El servidor de push rechazo la peticion: {e}")
except Exception as e:
    print(f"ERROR: {e}")
finally:
    db.close()
