from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def save_key_to_file(key_str: str, filename: str):
    with open(filename, 'w') as f:
        f.write(key_str)


from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def generate_rsa_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Serialize private key to PEM format
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,  # or TraditionalOpenSSL
        encryption_algorithm=serialization.NoEncryption()  # or BestAvailableEncryption(b"your_passphrase")
    )

    # Serialize public key to PEM format
    public_key = private_key.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return public_key_pem.decode(), private_key_pem.decode()
# ==============================SECURITY MODULE========================
# THE KEYS WERE VERIFIED  BY USING CURL AS BASED ON META EXAMPLE

"""Security Module."""

import json
from base64 import b64decode, b64encode
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.padding import MGF1, OAEP, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_pem_private_key


""" 
requirements

- cryptography
- fastapi
- base64

"""

private_key = Path(__file__).parent.parent / "private.pem"

PRIVATE_KEY = private_key.read_text(encoding="utf-8")

password=""

class Security:
    """Security class for encryption and decryption."""

    @staticmethod
    def decrypt_request(
        encrypted_flow_data_b64,
        encrypted_aes_key_b64,
        initial_vector_b64,
    ):
        flow_data = b64decode(encrypted_flow_data_b64)
        iv = b64decode(initial_vector_b64)

        # Decrypt the AES encryption key
        private_key = load_pem_private_key(
            PRIVATE_KEY.encode("utf-8"),
            password=None,
        )
        encrypted_aes_key = b64decode(encrypted_aes_key_b64)
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            OAEP(
                mgf=MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        # Decrypt the Flow data
        encrypted_flow_data_body = flow_data[:-16]
        encrypted_flow_data_tag = flow_data[-16:]
        decryptor = Cipher(
            algorithms.AES(aes_key),
            modes.GCM(iv, encrypted_flow_data_tag),
        ).decryptor()
        decrypted_data_bytes = (
            decryptor.update(encrypted_flow_data_body) + decryptor.finalize()
        )
        decrypted_data = json.loads(decrypted_data_bytes.decode("utf-8"))
        return decrypted_data, aes_key, iv

    @staticmethod
    def encrypt_response(response, aes_key, iv):
        # Flip the initialization vector
        flipped_iv = bytearray()
        for byte in iv:
            flipped_iv.append(byte ^ 0xFF)

        # Encrypt the response data
        encryptor = Cipher(algorithms.AES(aes_key), modes.GCM(flipped_iv)).encryptor()
        return b64encode(
            encryptor.update(json.dumps(response).encode("utf-8"))
            + encryptor.finalize()
            + encryptor.tag,
        ).decode("utf-8")



