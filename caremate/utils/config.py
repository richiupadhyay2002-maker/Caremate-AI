"""Configuration management for Caremate AI.

Centralizes all settings loaded from environment variables with sensible
defaults so that the system runs out-of-the-box with zero API keys.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

from pydantic import BaseModel, Field, computed_field

# Load .env file for local development (idempotent — won't override existing env vars)
load_dotenv()


def _getenv(key: str, default: str = "") -> str:
    """Read an environment variable, trimmed."""
    return os.environ.get(key, default).strip() if os.environ.get(key) else default


def _getenv_int(key: str, default: int) -> int:
    val = _getenv(key)
    try:
        return int(val) if val else default
    except ValueError:
        return default


def _getenv_bool(key: str, default: bool = False) -> bool:
    """Read *key* from the environment and parse as bool."""
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.lower() in ("1", "true", "yes", "on")


def _generate_secret() -> str:
    """Generate a cryptographically random secret (used as JWT fallback)."""
    import secrets as _secrets
    return _secrets.token_urlsafe(32)


class Settings(BaseModel):
    """Global configuration loaded from environment variables."""

    model_config = {"extra": "ignore"}

    # ------------------------------------------------------------------
    # Provider selection
    # ------------------------------------------------------------------
    llm_provider: str = Field(default_factory=lambda: _getenv("CAREMATE_LLM_PROVIDER", "mock"))
    embedding_provider: str = Field(default_factory=lambda: _getenv("CAREMATE_EMBEDDING_PROVIDER", "mock"))

    # ------------------------------------------------------------------
    # API keys (optional — mock provider needs none)
    # ------------------------------------------------------------------
    openai_api_key: Optional[str] = Field(default_factory=lambda: _getenv("OPENAI_API_KEY") or None)
    anthropic_api_key: Optional[str] = Field(default_factory=lambda: _getenv("ANTHROPIC_API_KEY") or None)
    groq_api_key: Optional[str] = Field(default_factory=lambda: _getenv("GROQ_API_KEY") or None)

    # ------------------------------------------------------------------
    # Model names
    # ------------------------------------------------------------------
    openai_model: str = Field(default_factory=lambda: _getenv("CAREMATE_OPENAI_MODEL", "gpt-4o-mini"))
    openai_embedding_model: str = Field(default_factory=lambda: _getenv("CAREMATE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
    anthropic_model: str = Field(default_factory=lambda: _getenv("CAREMATE_ANTHROPIC_MODEL", "claude-3-haiku-20240320"))
    groq_model: str = Field(default_factory=lambda: _getenv("CAREMATE_GROQ_MODEL", "llama-3.1-8b-instant"))

        # ------------------------------------------------------------------
    # Vector store
    # ------------------------------------------------------------------
    vector_dim: int = Field(default_factory=lambda: _getenv_int("CAREMATE_VECTOR_DIM", 384))
    top_k: int = Field(default_factory=lambda: _getenv_int("CAREMATE_TOP_K", 5))

    # ------------------------------------------------------------------
    # Database (Phase 2 persistence)
    # ------------------------------------------------------------------
    database_url: str = Field(
        default_factory=lambda: _getenv("CAREMATE_DATABASE_URL", "sqlite:///caremate.db"),
    )
    jwt_secret: str = Field(
        default_factory=lambda: _getenv("CAREMATE_JWT_SECRET") or _generate_secret(),
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(
        default_factory=lambda: _getenv_int("CAREMATE_JWT_EXPIRE_MINUTES", 1440),
    )

    # ------------------------------------------------------------------
    # Production security enforcement
    # ------------------------------------------------------------------
    force_prod_secrets: bool = Field(
        default_factory=lambda: _getenv_bool("CAREMATE_FORCE_PROD_SECRETS", False),
    )
    encryption_key: Optional[str] = Field(
        default_factory=lambda: _getenv("CAREMATE_ENCRYPTION_KEY") or None,
    )

    # ------------------------------------------------------------------
    # File upload (Phase 3 document ingestion)
    # ------------------------------------------------------------------
    upload_dir: str = Field(
        default_factory=lambda: _getenv("CAREMATE_UPLOAD_DIR", "./uploads"),
    )

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    log_level: str = Field(default_factory=lambda: _getenv("CAREMATE_LOG_LEVEL", "INFO"))

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    @computed_field  # type: ignore[misc]
    @property
    def is_mock_mode(self) -> bool:
        """True when no real API key is configured."""
        return not any([self.openai_api_key, self.anthropic_api_key, self.groq_api_key])

    @computed_field
    @property
    def effective_llm_provider(self) -> str:
        """Provider to use, falling back to mock when no key is present."""
        if self.llm_provider == "openai" and self.openai_api_key:
            return "openai"
        if self.llm_provider == "anthropic" and self.anthropic_api_key:
            return "anthropic"
        if self.llm_provider == "groq" and self.groq_api_key:
            return "groq"
        return "mock"


@lru_cache()
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached)."""
    return Settings()


# ------------------------------------------------------------------
# Production secret validation
# ------------------------------------------------------------------
def validate_prod_secrets(settings: "Settings | None" = None) -> None:
    """Refuse startup if production security is not properly configured.

    This check runs automatically during application startup **only** when
    ``force_prod_secrets`` is ``True`` (``CAREMATE_FORCE_PROD_SECRETS=true``).

    It guards against:

    * **JWT secret still being the auto-generated random default** — in
      development this is fine, but in production the secret should be
      explicitly provided via ``CAREMATE_JWT_SECRET`` and kept constant
      across instances.  When ``force_prod_secrets`` is set and the JWT
      secret was *not* read from the environment, we cannot distinguish an
      auto-generated secret from a default, so we require the env var to
      be present.

    * **Missing encryption key** — ``CAREMATE_ENCRYPTION_KEY`` should be
      set to a valid Fernet key (``pip install cryptography && python -c
      "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"``).

    Raises ``RuntimeError`` if any required secret is missing.
    """
    if settings is None:
        settings = get_settings()

    if not settings.force_prod_secrets:
        return

    # In production, the JWT secret must be explicitly provided via env var
    # rather than auto-generated, so it is stable across restarts/instances.
    if not os.environ.get("CAREMATE_JWT_SECRET"):
        raise RuntimeError(
            "CAREMATE_FORCE_PROD_SECRETS is enabled but CAREMATE_JWT_SECRET "
            "is not set. Set a strong, stable secret in production."
        )

    if not settings.encryption_key:
        raise RuntimeError(
            "CAREMATE_FORCE_PROD_SECRETS is enabled but "
            "CAREMATE_ENCRYPTION_KEY is not set. "
            "Generate a Fernet key: "
            "python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )


# ------------------------------------------------------------------
# Lightweight logging helper (avoids importing logging.config)
# ------------------------------------------------------------------
import logging


def get_logger(name: str = "caremate") -> logging.Logger:
    """Return a configured logger.

    All log handlers are automatically equipped with a
    :class:`~caremate.security.redaction.PhiRedactionFilter` that scrubs
    PII/PHI before output, ensuring no medical record content is ever
    written to logs.
    """
    # Import here to avoid circular import (config -> security -> db -> config)
    from caremate.security.redaction import PhiRedactionFilter

    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        # Attach PHI redaction filter so every log message is scrubbed
        handler.addFilter(PhiRedactionFilter())
        logger.addHandler(handler)
    settings = get_settings()
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    return logger

