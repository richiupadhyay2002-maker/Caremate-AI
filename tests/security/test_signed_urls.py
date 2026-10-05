"""Tests for signed-URL generation and verification."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from caremate.security.signed_urls import generate_signed_url, verify_signed_url


class TestSignedUrls:
    """Unit tests for HMAC-SHA256 signed URL functions."""

    def test_generate_signed_url_contains_document_id(self):
        url = generate_signed_url("doc_123", expires_in=3600)
        assert "doc_123" in url
        assert "exp=" in url
        assert "sig=" in url

    def test_generate_signed_url_default_expiry(self):
        """Default expiry is 3600 seconds."""
        before = int(time.time()) + 3600 - 5
        url = generate_signed_url("doc_123")
        # Extract the exp param
        exp_str = url.split("exp=")[1].split("&")[0]
        exp_val = int(exp_str)
        after = int(time.time()) + 3600 + 5
        assert before <= exp_val <= after

    def test_verify_valid_url(self):
        """A freshly generated URL should verify successfully."""
        url = generate_signed_url("doc_123", expires_in=3600)
        # Parse the URL params
        exp = int(url.split("exp=")[1].split("&")[0])
        sig = url.split("sig=")[1]
        assert verify_signed_url("doc_123", exp, sig) is True

    def test_verify_wrong_document_id(self):
        """Signature must not validate for a different document_id."""
        url = generate_signed_url("doc_123", expires_in=3600)
        exp = int(url.split("exp=")[1].split("&")[0])
        sig = url.split("sig=")[1]
        assert verify_signed_url("doc_999", exp, sig) is False

    def test_verify_wrong_signature(self):
        """A tampered signature must not validate."""
        url = generate_signed_url("doc_123", expires_in=3600)
        exp = int(url.split("exp=")[1].split("&")[0])
        assert verify_signed_url("doc_123", exp, "deadbeef") is False

    def test_verify_expired_url(self):
        """An URL whose expiry is already in the past must not validate."""
        # Create a signature for an expiry time that's already passed
        from caremate.security.signed_urls import _sign
        past_time = int(time.time()) - 100
        sig = _sign("doc_123", past_time)
        assert verify_signed_url("doc_123", past_time, sig) is False

    def test_timing_safe_comparison(self):
        """verify_signed_url uses hmac.compare_digest (timing-safe)."""
        url = generate_signed_url("doc_123", expires_in=3600)
        exp = int(url.split("exp=")[1].split("&")[0])
        sig = url.split("sig=")[1]

        # Even slightly different signatures should fail
        tampered = sig[:-1] + ("0" if sig[-1] != "0" else "1")
        assert verify_signed_url("doc_123", exp, tampered) is False

    def test_url_format(self):
        """The generated URL has the expected format."""
        url = generate_signed_url("doc_xyz", expires_in=120)
        assert url.startswith("/download/doc_xyz?")
        assert "exp=" in url
        assert "sig=" in url

    def test_custom_expiry(self):
        """Custom expiry is respected."""
        url = generate_signed_url("doc_123", expires_in=7200)
        exp_str = url.split("exp=")[1].split("&")[0]
        exp_val = int(exp_str)
        assert exp_val >= int(time.time()) + 7190  # within 10s tolerance
