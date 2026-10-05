"""ASGI entry point for uvicorn.

Usage::

    uvicorn caremate.api.asgi:app --reload
"""

from caremate.api.main import app  # noqa: F401
