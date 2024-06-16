from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import os

class AESEncryption:
    def __init__(self, key):
        # Initialize with the given AES key and generate a random IV (Initialization Vector)
        self.key = key
        self.iv = os.urandom(16)

    def encrypt(self, plaintext):
        # Create a Cipher object using AES algorithm in CFB mode with the generated IV
        cipher = Cipher(algorithms.AES(self.key), modes.CFB(self.iv))
        # Create an encryptor object from the cipher
        encryptor = cipher.encryptor()
        # Encrypt the plaintext and finalize the encryption
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        # Return the IV concatenated with the ciphertext
        return self.iv + ciphertext

    def decrypt(self, ciphertext):
        # Extract the IV from the beginning of the ciphertext
        iv = ciphertext[:16]
        # Create a Cipher object using AES algorithm in CFB mode with the extracted IV
        cipher = Cipher(algorithms.AES(self.key), modes.CFB(iv))
        # Create a decryptor object from the cipher
        decryptor = cipher.decryptor()
        # Decrypt the ciphertext and finalize the decryption
        plaintext = decryptor.update(ciphertext[16:]) + decryptor.finalize()
        return plaintext
