# Base64URL VAPID generator
from ecdsa import SigningKey, NIST256p
import base64

def generate_vapid_keys():
    # Private Key
    sk = SigningKey.generate(curve=NIST256p)
    # Public Key (uncompressed - must start with 0x04)
    vk = sk.get_verifying_key()
    
    private_key = base64.urlsafe_b64encode(sk.to_string()).decode("utf-8").strip("=")
    public_key = base64.urlsafe_b64encode(b"\x04" + vk.to_string()).decode("utf-8").strip("=")
    
    return private_key, public_key

if __name__ == "__main__":
    priv, pub = generate_vapid_keys()
    print(f"VAPID_PRIVATE_KEY={priv}")
    print(f"VAPID_PUBLIC_KEY={pub}")
