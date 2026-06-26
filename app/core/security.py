"""
Security utilities — password hashing, JWT generation & validation.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ─── Password Hashing ─────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT Tokens ───────────────────────────────────────────────────────────────
def create_access_token(
    subject: str | int,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        subject: Usually the user ID (stored in 'sub' claim).
        extra_claims: Additional claims to include (e.g., role, org_id).

    Returns:
        Signed JWT string.
    """
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
        "jti": secrets.token_hex(16),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token() -> tuple[str, str]:
    """
    Generate a refresh token pair: (raw_token, hashed_token).

    The raw token is returned to the client once.
    Only the hashed version is stored in the database.

    Returns:
        (raw_token, sha256_hash_of_token)
    """
    raw_token = secrets.token_urlsafe(64)
    hashed = _hash_refresh_token(raw_token)
    return raw_token, hashed


def _hash_refresh_token(token: str) -> str:
    """Hash a refresh token with SHA-256 before DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def hash_refresh_token(token: str) -> str:
    """Public wrapper for hashing refresh tokens."""
    return _hash_refresh_token(token)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Raises:
        JWTError: If the token is invalid or expired.
    """
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload


def create_api_key_secret() -> tuple[str, str]:
    """
    Generate an API key pair: (full_key, hashed_key).

    Format: vt_live_<random_48_chars>
    The prefix (first 12 chars) is stored in plain text for display.
    The full key is hashed before storage.

    Returns:
        (full_key, sha256_hash)
    """
    random_part = secrets.token_urlsafe(36)
    full_key = f"vt_live_{random_part}"
    hashed = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, hashed


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()
