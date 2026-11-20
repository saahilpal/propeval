from __future__ import annotations

import pytest
from backend.app.security.pii_redactor import (
    _VERHOEFF_D,
    _VERHOEFF_P,
    redact_pii_dpdp,
    validate_verhoeff_aadhaar,
)


def _generate_valid_aadhaar(first_11: str) -> str:
    """Generate a mathematically valid 12-digit Aadhaar with correct Verhoeff check digit."""
    c = 0
    reversed_digits = [int(d) for d in reversed(first_11)]
    for i, d in enumerate(reversed_digits):
        c = _VERHOEFF_D[c][_VERHOEFF_P[(i + 1) % 8][d]]
    check_digit = _VERHOEFF_D[c].index(0)
    return first_11 + str(check_digit)


def test_indian_mobile_fuzzing_all_formats():
    """Fuzz Indian mobile numbers across prefixes, spacing, punctuation, and Devanagari digits."""
    test_cases = [
        ("Call me on 9876543210 please", "[REDACTED_PHONE]"),
        ("My WhatsApp is +91 98765 43210", "[REDACTED_PHONE]"),
        ("Contact +91-98765-43210 immediately", "[REDACTED_PHONE]"),
        ("Phone: 9876 543 210", "[REDACTED_PHONE]"),
        ("Alternate: 987-654-3210", "[REDACTED_PHONE]"),
        ("Dial 09876543210 for sales", "[REDACTED_PHONE]"),
        ("मेरा फोन नंबर ९८७६५४३२१० है", "[REDACTED_PHONE]"),
        ("कृपया +९१ ९८७६५ ४३२१० पर कॉल करें", "[REDACTED_PHONE]"),
    ]

    for raw, expected_token in test_cases:
        redacted = redact_pii_dpdp(raw)
        assert expected_token in redacted, f"Failed for input: '{raw}', got: '{redacted}'"


def test_pan_redaction_fuzzing():
    """Verify PAN card scrubbing on valid patterns and mixed casing."""
    assert "[REDACTED_PAN]" in redact_pii_dpdp("My PAN is ABCDE1234F for registration")
    assert "[REDACTED_PAN]" in redact_pii_dpdp("pan card: abcde1234f")


def test_verhoeff_aadhaar_validation_and_rejection():
    """Verify Aadhaar numbers with valid Verhoeff are scrubbed; invalid checksums are preserved."""
    valid_aadhaar = _generate_valid_aadhaar("23456789012")
    assert validate_verhoeff_aadhaar(valid_aadhaar) is True

    # 1. Valid Aadhaar in text -> Redacted
    text_valid = f"Customer Aadhaar is {valid_aadhaar} for KYC"
    assert "[REDACTED_AADHAAR]" in redact_pii_dpdp(text_valid)

    # 2. Devanagari numerals valid Aadhaar -> Redacted
    dev_map = str.maketrans("0123456789", "०१२३४५६७८९")
    dev_aadhaar = valid_aadhaar.translate(dev_map)
    text_dev = f"आधार संख्या {dev_aadhaar} है"
    assert "[REDACTED_AADHAAR]" in redact_pii_dpdp(text_dev)

    # 3. Invalid Aadhaar (last digit corrupted) -> NOT redacted as Aadhaar
    invalid_last = str((int(valid_aadhaar[-1]) + 1) % 10)
    invalid_aadhaar = valid_aadhaar[:-1] + invalid_last
    assert validate_verhoeff_aadhaar(invalid_aadhaar) is False
    text_invalid = f"Reference code {invalid_aadhaar} was received"
    assert "[REDACTED_AADHAAR]" not in redact_pii_dpdp(text_invalid)

    # 4. 12-digit property/transaction figures (e.g. 100000000000) -> NOT redacted
    price_str = "Total valuation is 120000000000 INR"
    assert "[REDACTED_AADHAAR]" not in redact_pii_dpdp(price_str)


def test_rera_and_project_allowlist_preservation():
    """Ensure legitimate RERA IDs and project names are never accidentally redacted."""
    rera_id = "PRM/KA/RERA/1251/310/PR/170915/000123"
    project_name = "Godrej Woods Sector 43"

    sample_text = (
        f"Project {project_name} is registered under RERA {rera_id}. "
        "Sales rep Rahul phone +91 9876543210, PAN ABCDE1234F."
    )

    redacted = redact_pii_dpdp(sample_text, allowlist=[project_name, rera_id])

    assert project_name in redacted
    assert rera_id in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_PAN]" in redacted
    assert "+91 9876543210" not in redacted
    assert "ABCDE1234F" not in redacted
