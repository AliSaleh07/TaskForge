"""Authentication and authorization utilities: PBKDF2 password hashing and JWT."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Dict, Any, Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from taskforge.config import settings
from taskforge.database import get_db

# Security scheme for FastAPI OpenAPI docs
bearer_scheme = HTTPBearer(auto_error=False)

# PBKDF2 Configuration (NIST Guidelines)
HASH_ALGORITHM = "sha256"
ITERATIONS = 600_000
SALT_BYTES = 32


def hash_password(password: str) -> str:
    """Hash a password securely using PBKDF2-HMAC-SHA256 with 600k iterations and a fresh salt."""
    salt = secrets.token_bytes(SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode("utf-8"),
        salt,
        ITERATIONS,
        dklen=32,
    )
    salt_b64 = base64.b64encode(salt).decode("utf-8")
    hash_b64 = base64.b64encode(derived).decode("utf-8")
    return f"pbkdf2:{HASH_ALGORITHM}:{ITERATIONS}${salt_b64}${hash_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored PBKDF2 hash using constant-time comparison."""
    try:
        header, salt_b64, hash_b64 = hashed_password.split("$")
        parts = header.split(":")
        algo = parts[1]
        iterations = int(parts[2])
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        stored_hash = base64.b64decode(hash_b64.encode("utf-8"))

        candidate = hashlib.pbkdf2_hmac(
            algo,
            plain_password.encode("utf-8"),
            salt,
            iterations,
            dklen=len(stored_hash),
        )
        return hmac.compare_digest(candidate, stored_hash)
    except Exception:
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    padding = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode((s + padding).encode("utf-8"))


def create_access_token(data: Dict[str, Any], expires_delta_seconds: Optional[int] = None) -> str:
    """Create a cryptographically signed HMAC-SHA256 JWT access token."""
    now = int(time.time())
    delta = expires_delta_seconds or (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    exp = now + delta

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {**data, "iat": now, "exp": exp}

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Verify signature and expiration of an access token and return payload."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Malformed token")

        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        provided_sig = _b64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, provided_sig):
            raise ValueError("Invalid signature")

        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        exp = payload.get("exp")
        if exp is not None and int(exp) < int(time.time()):
            raise ValueError("Token has expired")

        return payload
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> Dict[str, Any]:
    """Dependency that extracts and validates the authenticated user from the Bearer token."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account no longer exists",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return dict(row)
