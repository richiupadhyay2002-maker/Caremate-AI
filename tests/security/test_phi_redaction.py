"""Tests for PHI / PII redaction utilities."""

from __future__ import annotations

import logging

from caremate.security.redaction import PhiRedactionFilter, redact_phi


class TestRedactPhi:
    """Unit tests for the :func:`redact_phi` function."""

    def test_redact_ssn(self):
        text = "Patient SSN is 123-45-6789 for reference."
        result = redact_phi(text)
        assert "123-45-6789" not in result
        assert "[REDACTED]" in result

    def test_redact_email(self):
        text = "Contact: john.doe@example.com"
        result = redact_phi(text)
        assert "john.doe@example.com" not in result
        assert "[REDACTED]" in result

    def test_redact_phone(self):
        text = "Call (555) 123-4567 or 555-987-6543."
        result = redact_phi(text)
        assert "555" not in result or "[REDACTED]" in result

    def test_redact_mrn(self):
        text = "MRN: 1234567"
        result = redact_phi(text)
        assert "1234567" not in result

    def test_redact_lab_values(self):
        text = "HbA1c: 7.2%, Sodium: 135, WBC 12.5"
        result = redact_phi(text)
        # At least one PHI pattern should be redacted
        assert "[REDACTED]" in result

    def test_redact_medications(self):
        text = "Take warfarin 5mg daily and lisinopril 10mg."
        result = redact_phi(text)
        assert "warfarin" not in result.lower() or "[REDACTED]" in result
        assert "lisinopril" not in result.lower() or "[REDACTED]" in result

    def test_redact_dob(self):
        text = "DOB 01/15/1950"
        result = redact_phi(text)
        assert "01/15/1950" not in result
        assert "[REDACTED]" in result

    def test_redact_age(self):
        text = "65-year-old patient, age 70 y/o"
        result = redact_phi(text)
        assert "[REDACTED]" in result

    def test_no_false_positives_on_safe_text(self):
        text = "The patient was seen today for a routine checkup."
        result = redact_phi(text)
        assert "patient" in result  # 'patient' itself should not be redacted

    def test_none_input(self):
        assert redact_phi(None) == ""

    def test_non_string_input(self):
        result = redact_phi(12345)
        assert isinstance(result, str)
        assert "12345" in result  # ints are just converted to str


class TestPhiRedactionFilter:
    """Tests for the :class:`PhiRedactionFilter` logging filter."""

    def test_filter_redacts_log_message(self, caplog):
        """PHI in log messages is redacted before reaching handlers."""
        handler = logging.StreamHandler()
        handler.addFilter(PhiRedactionFilter())
        logger = logging.getLogger("test_redaction_filter")
        logger.handlers = [handler]
        logger.setLevel(logging.WARNING)

        ssn = "987-65-4321"
        with caplog.at_level(logging.WARNING):
            logger.warning("Patient SSN: %s", ssn)

        # The captured log should NOT contain the raw SSN
        assert ssn not in caplog.text
        assert "[REDACTED]" in caplog.text

    def test_filter_never_crashes(self):
        """The filter must never raise, even on weird records."""
        flt = PhiRedactionFilter()

        class FakeRecord:
            msg = 12345
            args = None

        assert flt.filter(FakeRecord()) is True

    def test_filter_handles_args(self, caplog):
        """PHI in log args is also redacted."""
        handler = logging.StreamHandler()
        handler.addFilter(PhiRedactionFilter())
        logger = logging.getLogger("test_redaction_args")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)

        with caplog.at_level(logging.INFO):
            logger.info("Lab result: HbA1c=%s", "7.2%")

        # Should not contain raw PHI
        assert "HbA1c" not in caplog.text or "[REDACTED]" in caplog.text
