from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

def generate_vapid_keys():
    # Generate P-256 private key
    private_key = ec.generate_private_key(ec.SECP256R1())
    
    # Get raw private bytes (32 bytes)
    private_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
    private_base64 = base64.urlsafe_b64encode(private_bytes).decode('utf-8').strip('=')
    
    # Get raw public bytes (65 bytes: 0x04 + X + Y)
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    public_base64 = base64.urlsafe_b64encode(public_bytes).decode('utf-8').strip('=')
    
    return private_base64, public_base64

if __name__ == "__main__":
    priv, pub = generate_vapid_keys()
    print(f"VAPID_PRIVATE_KEY={priv}")
    print(f"VAPID_PUBLIC_KEY={pub}")
