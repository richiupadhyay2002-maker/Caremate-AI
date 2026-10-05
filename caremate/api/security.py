"""Authentication & authorization utilities for the Caremate API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from caremate.db.models_core import User, UserRole
from caremate.utils.config import get_settings

_settings = get_settings()

# Use pbkdf2_sha256 — pure-Python backend, no bcrypt version-detection issues
# across different platform builds.  Still provides salted, iterated hashing.
_pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a password using bcrypt."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return _pwd_context.verify(plain, hashed)


def create_access_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token for a user.

    The token embeds ``sub`` (user id), ``role``, and ``patient_id``/``doctor_id``
    claims so downstream endpoints can enforce RBAC without a DB round-trip
    on every request (the claim is re-validated against the DB session).
    """
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=_settings.jwt_expire_minutes))
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "patient_id": user.patient_id,
        "doctor_id": user.doctor_id,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    return jwt.encode(payload, _settings.jwt_secret, algorithm=_settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Raises ``JWTError`` (or its subclasses) if the token is invalid/expired.
    """
    return jwt.decode(token, _settings.jwt_secret, algorithms=[_settings.jwt_algorithm])
