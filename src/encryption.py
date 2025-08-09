"""
Encryption Module
Handles encryption and decryption of sensitive data like passwords.
"""

from cryptography.fernet import Fernet
from config import config
import base64
import os

# --- KEY MANAGEMENT ---
# It's better to load the key from a file or environment variable.
# For simplicity, we'll derive it from the SECRET_KEY.
# In a real production app, use a more robust key management system.
def _get_key() -> bytes:
    """
    Derives a valid Fernet key from the app's SECRET_KEY.
    The key must be 32 bytes and URL-safe base64 encoded.
    """
    secret = config.SECRET_KEY
    # Ensure the key is 32 bytes long
    hashed_secret = base64.urlsafe_b64encode(secret.ljust(32)[:32].encode('utf-8'))
    return hashed_secret

# Initialize Fernet with the derived key
try:
    cipher_suite = Fernet(_get_key())
except Exception as e:
    print(f"FATAL: Could not initialize encryption suite. Ensure SECRET_KEY is set. Error: {e}")
    # In a real app, you might want to exit or handle this more gracefully.
    cipher_suite = None

# --- ENCRYPTION/DECRYPTION FUNCTIONS ---

def encrypt_password(password: str) -> str:
    """Encrypts a password."""
    if not cipher_suite:
        raise ValueError("Encryption suite not initialized.")
    if not password:
        return ""

    encrypted_text = cipher_suite.encrypt(password.encode('utf-8'))
    return encrypted_text.decode('utf-8')

def decrypt_password(encrypted_password: str) -> str:
    """Decrypts a password."""
    if not cipher_suite:
        raise ValueError("Encryption suite not initialized.")
    if not encrypted_password:
        return ""

    decrypted_text = cipher_suite.decrypt(encrypted_password.encode('utf-8'))
    return decrypted_text.decode('utf-8')
