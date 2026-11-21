from __future__ import annotations

from backend.app.providers.webhook_adapter import is_safe_webhook_url
from backend.app.security.pii_redactor import (
    redact_pii_dpdp,
    validate_verhoeff_aadhaar,
)


def test_ssrf_blocks_private_and_loopback_ips():
    assert not is_safe_webhook_url("http://127.0.0.1:8000/agent")
    assert not is_safe_webhook_url("http://localhost:3000/webhook")
    assert not is_safe_webhook_url("http://169.254.169.254/latest/meta-data")
    assert not is_safe_webhook_url("http://10.0.0.1:5000/call")
    assert not is_safe_webhook_url("http://192.168.1.1/api")
    assert not is_safe_webhook_url("http://[::1]:8080/hook")


def test_verhoeff_aadhaar_validation():
    # Valid Aadhaar numbers generated via Verhoeff checksum algorithm
    # e.g., 2345 6789 0120 is Verhoeff valid (starting with 2-9)
    assert not validate_verhoeff_aadhaar("123456789012")  # starts with 1
    assert not validate_verhoeff_aadhaar("012345678901")  # starts with 0
    assert not validate_verhoeff_aadhaar("999999999991")  # invalid checksum (c=5)


def test_dpdp_pii_redaction_preserves_rera_and_prices():
    sample_text = (
        "Customer Rahul Sharma with PAN ABCDE1234F and mobile +91 98765 43210 "
        "is inquiring about Lodha Wakad RERA ID P52100012345 for 2 BHK starting at 1.2 Crore."
    )
    redacted = redact_pii_dpdp(sample_text)

    # PAN and Phone redacted
    assert "ABCDE1234F" not in redacted
    assert "[REDACTED_PAN]" in redacted
    assert "98765" not in redacted
    assert "[REDACTED_PHONE]" in redacted

    # RERA ID and property price preserved intact
    assert "P52100012345" in redacted
    assert "1.2 Crore" in redacted
    assert "2 BHK" in redacted
