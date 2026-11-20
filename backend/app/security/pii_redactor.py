from __future__ import annotations

import re

# Devanagari to ASCII digit translation
DEVANAGARI_DIGITS = "०१२३४५६७८९"
ASCII_DIGITS = "0123456789"
DEV_TO_ASCII = str.maketrans(DEVANAGARI_DIGITS, ASCII_DIGITS)

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
    """Validate 12-digit Aadhaar checksum using Verhoeff algorithm.

    Translates Devanagari numerals to ASCII digits if present.
    """
    ascii_str = number_str.translate(DEV_TO_ASCII)
    digits = re.sub(r"\D", "", ascii_str)
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


# PAN Card Regex: 5 letters, 4 digits, 1 letter
PAN_REGEX = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b", re.IGNORECASE)

# Indian Mobile Regex: optional (+91, 91, 0, +९१, ९१, ०) followed by 10 digits starting with 6-9 or ६-९
ALL_6_9 = r"[6-9६-९]"
ALL_DIGITS = r"[\d०-९]"
PHONE_REGEX = re.compile(
    rf"(?:(?:\+?91|91|0|\+?९१|९१|०)[\s\-]?)?({ALL_6_9}(?:[\s\-]*{ALL_DIGITS}){{9}})\b"
)

# Potential 12-digit Aadhaar patterns (ASCII or Devanagari)
AADHAAR_CANDIDATE_REGEX = re.compile(
    rf"\b({ALL_DIGITS}{{4}}[\s\-]?{ALL_DIGITS}{{4}}[\s\-]?{ALL_DIGITS}{{4}})\b"
)


def redact_pii_dpdp(
    text: str,
    allowlist: list[str] | set[str] | None = None,
) -> str:
    """Scrub Indian PII (Phone, PAN, Verhoeff-valid Aadhaar) while preserving RERA IDs and property figures.

    Parameters:
        text: Untrusted transcript or string.
        allowlist: Optional set of strings (e.g. project names, RERA IDs) that should never be redacted.
    """
    if not text:
        return text

    # Protect allowlisted terms with placeholders
    placeholders: dict[str, str] = {}
    result = text
    if allowlist:
        for idx, term in enumerate(sorted(allowlist, key=lambda s: -len(s))):
            if term and term in result:
                token = f"__ALLOWLIST_TOKEN_{idx}__"
                placeholders[token] = term
                result = result.replace(term, token)

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
        digits_raw = match.group(1).translate(DEV_TO_ASCII)
        digits = re.sub(r"\D", "", digits_raw)
        if len(digits) == 10 and digits[0] in "6789":
            return "[REDACTED_PHONE]"
        return matched_str

    result = PHONE_REGEX.sub(_phone_sub, result)

    # Restore allowlisted terms
    for token, original in placeholders.items():
        result = result.replace(token, original)

    return result
