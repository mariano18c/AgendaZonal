import os
import json
from pywebpush import webpush, WebPushException
from app.config import VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, VAPID_CLAIM_EMAIL

print(f"VAPID_PUBLIC_KEY (len): {len(VAPID_PUBLIC_KEY)}")
print(f"VAPID_PRIVATE_KEY (len): {len(VAPID_PRIVATE_KEY)}")

dummy_subscription = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/dummy",
    "keys": {
        "p256dh": "BLCcS674o0c3X9sP_m_M",
        "auth": "fXw-p_v-V"
    }
}

try:
    # This will fail on the push server but we want to see if webpush() throws an internal error before sending
    webpush(
        subscription_info=dummy_subscription,
        data="test",
        vapid_private_key=VAPID_PRIVATE_KEY,
        vapid_claims={"sub": VAPID_CLAIM_EMAIL}
    )
except WebPushException as e:
    # 400/401 is expected from dummy, but if it throws a cryptography error, the key is bad
    print(f"WebPushException: {e.response.status_code if e.response else 'No status'}")
except Exception as e:
    print(f"General Exception (Keys?): {e}")
