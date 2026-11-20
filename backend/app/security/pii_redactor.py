from __future__ import annotations

import re

# Verhoeff algorithm multiplication and permutation tables for Aadhaar validation
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def validate_verhoeff_aadhaar(number_str: str) -> bool:
    """Validate 12-digit Aadhaar checksum using Verhoeff algorithm."""
    digits = re.sub(r"\D", "", number_str)
    if len(digits) != 12:
        return False
    # Aadhaar first digit cannot be 0 or 1
    if digits[0] in ("0", "1"):
        return False

    c = 0
    reversed_digits = [int(d) for d in reversed(digits)]
    for i, d in enumerate(reversed_digits):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][d]]
    return c == 0


# PAN Card Regex: 5 letters (4th is status e.g. P/C/F), 4 digits, 1 letter
PAN_REGEX = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b", re.IGNORECASE)

# Indian Phone Regex: optional +91, 0, or space/dash with 10 digits starting with 6-9
PHONE_REGEX = re.compile(
    r"(?:(?:\+91|91|0)[\s\-]?)?([6-9]\d{4}[\s\-]?\d{5})\b"
)

# Potential 12-digit Aadhaar patterns (e.g., "1234 5678 9012" or "1234-5678-9012" or "123456789012")
AADHAAR_CANDIDATE_REGEX = re.compile(r"\b(\d{4}[\s\-]?\d{4}[\s\-]?\d{4})\b")


def redact_pii_dpdp(text: str) -> str:
    """Scrub Indian PII (Phone, PAN, Verhoeff-valid Aadhaar) while preserving RERA IDs and property figures."""
    if not text:
        return text

    result = text

    # 1. Redact PAN Cards
    result = PAN_REGEX.sub("[REDACTED_PAN]", result)

    # 2. Redact Verhoeff-valid Aadhaar (distinguish from 12-digit property/transaction IDs)
    def _aadhaar_sub(match: re.Match) -> str:
        candidate = match.group(1)
        if validate_verhoeff_aadhaar(candidate):
            return "[REDACTED_AADHAAR]"
        return candidate

    result = AADHAAR_CANDIDATE_REGEX.sub(_aadhaar_sub, result)

    # 3. Redact Indian Mobile Numbers
    def _phone_sub(match: re.Match) -> str:
        matched_str = match.group(0)
        # Avoid redacting prices like "9000000000" if context is currency
        digits = re.sub(r"\D", "", match.group(1))
        if len(digits) == 10 and digits[0] in "6789":
            return "[REDACTED_PHONE]"
        return matched_str

    result = PHONE_REGEX.sub(_phone_sub, result)

    return result
