import logging
import json
from app.database import SessionLocal
from app.models.push_subscription import PushSubscription
from app.routes.notifications import VAPID_PRIVATE_KEY, VAPID_CLAIM_EMAIL
from pywebpush import webpush, WebPushException

logging.basicConfig(level=logging.INFO)
db = SessionLocal()

try:
    sub = db.query(PushSubscription).filter(PushSubscription.id == 17).first()
    if not sub:
        print("Error: Suscripción 17 no encontrada.")
    else:
        print(f"Probando envio a ID 17, Endpoint: {sub.endpoint[:50]}...")
        payload = json.dumps({
            "title": "Prueba ID 17",
            "body": "Verificando llegada al navegador...",
            "url": "/"
        })
        
        try:
            res = webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth}
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIM_EMAIL}
            )
            print(f"EXITO: Status {res.status_code}")
        except WebPushException as e:
            print(f"FALLO: {e}")
except Exception as e:
    print(f"ERROR: {e}")
finally:
    db.close()
