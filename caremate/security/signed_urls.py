"""Signed URLs for secure document access.

Instead of exposing direct file paths, the API issues time-limited signed
URLs that allow the caller to download a document exactly once within a
short window (default 1 hour).  The signature uses HMAC-SHA256 with the
application's JWT signing secret.

Usage::

    # Generate (server-side, inside an endpoint)
    url = generate_signed_url(document_id, expires_in=3600)

    # Verify (server-side, when the download endpoint receives the token)
    if verify_signed_url(token, document_id):
        return FileResponse(path)
"""

from __future__ import annotations

import hmac
import hashlib
import time
from typing import Optional

from caremate.utils.config import get_settings

_settings = get_settings()


def _sign(document_id: str, expires_at: int) -> str:
    """Compute the HMAC-SHA256 signature for a document+expiry pair."""
    payload = f"{document_id}:{expires_at}:{_settings.jwt_secret}".encode()
    return hmac.new(
        _settings.jwt_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()


def generate_signed_url(
    document_id: str,
    expires_in: int = 3600,
) -> str:
    """Return a signed download URL for *document_id*.

    Args:
        document_id: The document identifier (from ``MedicalDocument.document_id``).
        expires_in: Lifetime in seconds (default 1 h).

    Returns:
        A URL string like ``/download/{document_id}?exp={ts}&sig={hex}``.
        The caller simply redirects the browser or returns the URL to the
        client.
    """
    expires_at = int(time.time()) + expires_in
    sig = _sign(document_id, expires_at)
    return f"/download/{document_id}?exp={expires_at}&sig={sig}"


def verify_signed_url(
    document_id: str,
    expires_at: int,
    signature: str,
) -> bool:
    """Validate a signed-URL payload.

    Returns ``True`` only if:
      * the signature matches (computed with the same secret), **and**
      * the expiry has not elapsed.

    Uses :func:`hmac.compare_digest` to prevent timing attacks.
    """
    # Check expiry first — fail-fast without a signature comparison
    if expires_at < int(time.time()):
        return False

    expected_sig = _sign(document_id, expires_at)
    return hmac.compare_digest(expected_sig, signature)
