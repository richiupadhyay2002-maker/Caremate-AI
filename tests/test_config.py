"""Comprehensive unit tests for caremate.utils.config.

Covers:
- Positive cases (env parsing, defaults, computed fields, logging)
- Negative cases (invalid values, missing env)
- Edge cases (whitespace trimming, bad ints, bool parsing, lru_cache,
  prod-secret validation)
"""

import logging
import pytest

from caremate.utils.config import (
    Settings,
    _getenv,
    _getenv_bool,
    _getenv_int,
    get_logger,
    get_settings,
    validate_prod_secrets,
)


# ---------------------------------------------------------------------------
# _getenv / _getenv_int / _getenv_bool
# ---------------------------------------------------------------------------

class TestGetenvHelpers:
    def test_returns_default_when_missing(self, monkeypatch):
        monkeypatch.delenv("SOME_TEST_KEY", raising=False)
        assert _getenv("SOME_TEST_KEY", "fallback") == "fallback"

    def test_returns_value_when_set(self, monkeypatch):
        monkeypatch.setenv("SOME_TEST_KEY", "hello")
        assert _getenv("SOME_TEST_KEY") == "hello"

    def test_trims_whitespace(self, monkeypatch):
        monkeypatch.setenv("SOME_TEST_KEY", "  padded  ")
        assert _getenv("SOME_TEST_KEY") == "padded"

    def test_whitespace_only_value_strips_to_empty(self, monkeypatch):
        """Documented quirk: whitespace-only values strip to '' (not default)."""
        monkeypatch.setenv("SOME_TEST_KEY", "   ")
        assert _getenv("SOME_TEST_KEY", "dflt") == ""

    def test_getenv_int_valid(self, monkeypatch):
        monkeypatch.setenv("SOME_INT_KEY", "42")
        assert _getenv_int("SOME_INT_KEY", 0) == 42

    def test_getenv_int_missing_returns_default(self, monkeypatch):
        monkeypatch.delenv("SOME_INT_KEY", raising=False)
        assert _getenv_int("SOME_INT_KEY", 7) == 7

    def test_getenv_int_invalid_returns_default(self, monkeypatch):
        monkeypatch.setenv("SOME_INT_KEY", "not-a-number")
        assert _getenv_int("SOME_INT_KEY", 7) == 7

    def test_getenv_bool_true_values(self, monkeypatch):
        for raw in ("1", "true", "TRUE", "yes", "on", "Yes"):
            monkeypatch.setenv("SOME_BOOL_KEY", raw)
            assert _getenv_bool("SOME_BOOL_KEY") is True

    def test_getenv_bool_false_values(self, monkeypatch):
        for raw in ("0", "false", "no", "off", "anything-else"):
            monkeypatch.setenv("SOME_BOOL_KEY", raw)
            assert _getenv_bool("SOME_BOOL_KEY") is False

    def test_getenv_bool_missing_returns_default(self, monkeypatch):
        monkeypatch.delenv("SOME_BOOL_KEY", raising=False)
        assert _getenv_bool("SOME_BOOL_KEY", default=True) is True


# ---------------------------------------------------------------------------
# Settings model
# ---------------------------------------------------------------------------

class TestSettings:
    def test_zero_key_defaults_to_mock(self, monkeypatch):
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        s = Settings()
        assert s.is_mock_mode is True
        assert s.effective_llm_provider == "mock"

    @pytest.mark.parametrize("env_key,provider", [
        ("OPENAI_API_KEY", "openai"),
        ("ANTHROPIC_API_KEY", "anthropic"),
        ("GROQ_API_KEY", "groq"),
    ])
    def test_effective_provider_with_key(self, monkeypatch, env_key, provider):
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv(f"CAREMMATE_LLM_PROVIDER", provider)
        monkeypatch.setenv(env_key, "test-key-123")
        s = Settings()
        assert s.is_mock_mode is False
        assert s.effective_llm_provider == provider

    def test_provider_selected_without_key_falls_back_to_mock(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("CAREMMATE_LLM_PROVIDER", "openai")
        s = Settings()
        assert s.effective_llm_provider == "mock"

    def test_unknown_provider_falls_back_to_mock(self):
        s = Settings(llm_provider="banana")
        assert s.effective_llm_provider == "mock"

    def test_unknown_llm_provider_without_key(self):
        s = Settings(llm_provider="unknown_provider")
        assert s.effective_llm_provider == "mock"

    def test_jwt_secret_auto_generated_when_missing(self, monkeypatch):
        monkeypatch.delenv("CAREMMATE_JWT_SECRET", raising=False)
        s1 = Settings()
        s2 = Settings()
        assert s1.jwt_secret != s2.jwt_secret  # each instance gets a fresh secret
        assert len(s1.jwt_secret) >= 32

    def test_jwt_secret_from_env_is_stable(self, monkeypatch):
        monkeypatch.setenv("CAREMMATE_JWT_SECRET", "super-secret-value")
        s = Settings()
        assert s.jwt_secret == "super-secret-value"

    def test_vector_dim_and_top_k_from_env(self, monkeypatch):
        monkeypatch.setenv("CAREMMATE_VECTOR_DIM", "128")
        monkeypatch.setenv("CAREMMATE_TOP_K", "10")
        s = Settings()
        assert s.vector_dim == 128
        assert s.top_k == 10

    def test_extra_fields_ignored(self):
        s = Settings(some_unknown_field="whatever")
        assert not hasattr(s, "some_unknown_field")


# ---------------------------------------------------------------------------
# get_settings singleton
# ---------------------------------------------------------------------------

class TestGetSettings:
    def test_cached_singleton(self):
        get_settings.cache_clear()
        a = get_settings()
        b = get_settings()
        assert a is b

    def test_cache_clear_creates_new_instance(self, monkeypatch):
        get_settings.cache_clear()
        monkeypatch.setenv("CAREMMATE_TOP_K", "3")
        a = get_settings()
        assert a.top_k == 3
        get_settings.cache_clear()
        b = get_settings()
        assert a is not b


# ---------------------------------------------------------------------------
# validate_prod_secrets
# ---------------------------------------------------------------------------

class TestValidateProdSecrets:
    def _settings(self, **overrides):
        s = Settings()
        for k, v in overrides.items():
            setattr(s, k, v)
        return s

    def test_noop_when_force_prod_secrets_false(self, monkeypatch):
        monkeypatch.delenv("CAREMMATE_JWT_SECRET", raising=False)
        validate_prod_secrets(self._settings(force_prod_secrets=False))  # no raise

    def test_raises_when_jwt_secret_missing_from_env(self, monkeypatch):
        monkeypatch.delenv("CAREMMATE_JWT_SECRET", raising=False)
        s = self._settings(force_prod_secrets=True, encryption_key="fernet-key")
        with pytest.raises(RuntimeError, match="CAREMMATE_JWT_SECRET"):
            validate_prod_secrets(s)

    def test_raises_when_encryption_key_missing(self, monkeypatch):
        monkeypatch.setenv("CAREMMATE_JWT_SECRET", "stable-secret")
        s = self._settings(force_prod_secrets=True, encryption_key=None)
        with pytest.raises(RuntimeError, match="CAREMMATE_ENCRYPTION_KEY"):
            validate_prod_secrets(s)

    def test_passes_when_both_provided(self, monkeypatch):
        monkeypatch.setenv("CAREMMATE_JWT_SECRET", "stable-secret")
        s = self._settings(force_prod_secrets=True, encryption_key="fernet-key")
        validate_prod_secrets(s)  # no raise

    def test_jwt_secret_checked_before_encryption_key(self, monkeypatch):
        """Both missing -> JWT error surfaces first."""
        monkeypatch.delenv("CAREMMATE_JWT_SECRET", raising=False)
        s = self._settings(force_prod_secrets=True, encryption_key=None)
        with pytest.raises(RuntimeError, match="JWT"):
            validate_prod_secrets(s)


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------

class TestGetLogger:
    def test_returns_logger(self):
        assert isinstance(get_logger("unit_test_logger"), logging.Logger)

    def test_same_logger_instance_reused(self):
        a = get_logger("unit_test_logger_2")
        b = get_logger("unit_test_logger_2")
        assert a is b

    def test_default_logger_name(self):
        assert get_logger().name == "caremate"

    def test_invalid_log_level_falls_back_to_info(self, monkeypatch):
        monkeypatch.setenv("CAREMMATE_LOG_LEVEL", "NOT_A_LEVEL")
        get_settings.cache_clear()
        try:
            logger = get_logger("unit_test_logger_3")
            assert logger.level == logging.INFO
        finally:
            get_settings.cache_clear()

    def test_valid_log_level_applied(self, monkeypatch):
        monkeypatch.setenv("CAREMMATE_LOG_LEVEL", "DEBUG")
        get_settings.cache_clear()
        try:
            logger = get_logger("unit_test_logger_4")
            assert logger.level == logging.DEBUG
        finally:
            get_settings.cache_clear()
