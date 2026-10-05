"""FastAPI dependencies for authentication and RBAC.

Usage::

    from fastapi import Depends
    from caremate.api.deps import require_patient

    @router.get("/me")
    def get_me(user = Depends(require_patient)):
        ...

``require_patient``, ``require_doctor``, and ``require_admin`` are *dependency
callables* — they take no arguments and return the authenticated ``User``
after enforcing the role check.  ``get_current_user`` returns any active user
regardless of role.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from caremate.api.security import decode_access_token
from caremate.db.models_core import User, UserRole
from caremate.db.session import get_db

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)


def _get_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def get_current_user(
    token: str = Depends(_get_token),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the current authenticated user from the JWT bearer token.

    Raises 401 if the token is missing/invalid/expired, 404 if the user
    record is not found, 403 if the user is inactive.
    """
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    return user


def _require_role(roles: set[UserRole]):
    """Return a dependency callable that enforces membership in *roles*."""

    def _checker(
        user: User = Depends(get_current_user),
    ) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this operation",
            )
        return user

    return _checker


# ------------------------------------------------------------------
# Public dependency callables (import these in your routers)
# ------------------------------------------------------------------
require_admin = _require_role({UserRole.ADMIN})
require_doctor = _require_role({UserRole.DOCTOR, UserRole.ADMIN})
require_patient = _require_role({UserRole.PATIENT, UserRole.ADMIN})

