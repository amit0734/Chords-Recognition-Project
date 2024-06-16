from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

class RSAEncryption:
    def __init__(self):
        # Generate a new private key using RSA algorithm with a public exponent of 65537 and a key size of 2048 bits
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        # Derive the public key from the private key
        self.public_key = self.private_key.public_key()

    def get_public_key_pem(self):
        # Return the public key in PEM format
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def encrypt(self, message, public_key_pem):
        # Load the public key from PEM format
        public_key = serialization.load_pem_public_key(public_key_pem)
        # Encrypt the message using the public key and OAEP padding with SHA-256
        encrypted = public_key.encrypt(
            message,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return encrypted

    def decrypt(self, encrypted_message):
        # Decrypt the encrypted message using the private key and OAEP padding with SHA-256
        decrypted = self.private_key.decrypt(
            encrypted_message,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted
