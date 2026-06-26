"""
Cryptographic utilities for API key generation.
"""

import hashlib
import secrets


def generate_api_key() -> tuple[str, str]:
    """
    Generate a VeriTrust API key pair.

    Format: vt_live_<url-safe-base64(48 random bytes)>

    Returns:
        (full_key, sha256_hash) — store only the hash in the database.
    """
    random_part = secrets.token_urlsafe(48)
    full_key = f"vt_live_{random_part}"
    hashed = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, hashed


def hash_string(value: str) -> str:
    """SHA-256 hash a string value."""
    return hashlib.sha256(value.encode()).hexdigest()
