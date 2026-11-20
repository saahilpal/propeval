"""Indian Currency and Real Estate Unit Normalizer for PropEval.

Architecture Spec: docs/09_EVALUATION_METHODOLOGY.md & ADR-004
Handles Indian currency expressions (lakh, crore, peti, khoka, Hinglish numbers like 'dedh',
'dhai', 'sawa', 'paune'), carpet area units, and BHK formats.
"""

from __future__ import annotations

import re

HINDI_NUMBERS: dict[str, float] = {
    "zero": 0.0,
    "ek": 1.0,
    "do": 2.0,
    "teen": 3.0,
    "char": 4.0,
    "chaar": 4.0,
    "paanch": 5.0,
    "panch": 5.0,
    "chhe": 6.0,
    "che": 6.0,
    "saat": 7.0,
    "aath": 8.0,
    "nau": 9.0,
    "das": 10.0,
    "gyarah": 11.0,
    "barah": 12.0,
    "terah": 13.0,
    "chaudah": 14.0,
    "pandrah": 15.0,
    "solah": 16.0,
    "satrah": 17.0,
    "atharah": 18.0,
    "unnis": 19.0,
    "bees": 20.0,
    "pachees": 25.0,
    "tees": 30.0,
    "paintees": 35.0,
    "chalis": 40.0,
    "pachaas": 50.0,
    "pachas": 50.0,
    "saath": 60.0,
    "sattar": 70.0,
    "assi": 80.0,
    "nabbe": 90.0,
    "sau": 100.0,
    "so": 100.0,
}

COLLOQUIAL_MULTIPLIERS: dict[str, float] = {
    "sawa": 1.25,
    "dedh": 1.5,
    "dhai": 2.5,
    "paune do": 1.75,
    "paune teen": 2.75,
    "paune char": 3.75,
    "paune": 0.75,
}

DENOMINATIONS: dict[str, float] = {
    "cr": 10_000_000.0,
    "crore": 10_000_000.0,
    "crores": 10_000_000.0,
    "koti": 10_000_000.0,
    "khoka": 10_000_000.0,
    "lakh": 100_000.0,
    "lac": 100_000.0,
    "lakhs": 100_000.0,
    "lacs": 100_000.0,
    "peti": 100_000.0,
    "k": 1_000.0,
    "thousand": 1_000.0,
    "hazaar": 1_000.0,
    "hazar": 1_000.0,
}


def _clean_text(text: str) -> str:
    cleaned = text.lower().strip()
    cleaned = cleaned.replace(",", "")
    cleaned = re.sub(r"[₹]|rs\.?|inr", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def parse_indian_currency(text: str | float) -> int | None:
    """Parse an Indian currency string, float, or integer into exact integer INR.

    Examples:
        '1.2 cr' -> 12000000
        '120 lakh' -> 12000000
        'ek crore bees lakh' -> 12000000
        'dedh crore' -> 15000000
        '₹ 1,20,00,000' -> 12000000
        '50 peti' -> 5000000
    """
    if isinstance(text, (int, float)):
        return round(text)

    if not isinstance(text, str):
        return None

    raw = _clean_text(text)
    if not raw:
        return None

    # Check for direct integer / float with no suffixes
    if re.fullmatch(r"^\d+(\.\d+)?$", raw):
        # Avoid treating 10-digit Indian phone numbers as plain currency
        if len(raw) == 10 and raw[0] in "6789":
            return None
        val = float(raw)
        return round(val)

    total_inr: float = 0.0
    matched = False

    # Check for Hinglish colloquial prefixes like 'dedh crore', 'dhai crore', 'sawa crore'
    for col_key, multiplier in sorted(COLLOQUIAL_MULTIPLIERS.items(), key=lambda x: -len(x[0])):
        pattern = rf"\b{col_key}\s+(crore|cr|lakh|lac|peti|khoka)\b"
        match = re.search(pattern, raw)
        if match:
            denom_key = match.group(1)
            unit_val = DENOMINATIONS.get(denom_key, 1.0)
            total_inr += multiplier * unit_val
            raw = raw.replace(match.group(0), " ").strip()
            matched = True

    # Check for spoken decimals like 'ek point do crore' -> 1.2 crore
    point_match = re.search(r"\b([a-z]+)\s+point\s+([a-z]+|\d+)\s+(crore|cr|lakh|lac)\b", raw)
    if point_match:
        w1, w2, denom = point_match.groups()
        n1 = HINDI_NUMBERS.get(w1, 1.0)
        n2 = float(HINDI_NUMBERS.get(w2, float(w2) if w2.isdigit() else 0.0))
        dec_val = n1 + (n2 / (10 ** len(str(int(n2)))) if n2 > 0 else 0.0)
        total_inr += dec_val * DENOMINATIONS.get(denom, 1.0)
        raw = raw.replace(point_match.group(0), " ").strip()
        matched = True

    # Check for Hinglish spoken digits with denominations (e.g. 'ek crore', 'bees lakh')
    for word_num, num_val in sorted(HINDI_NUMBERS.items(), key=lambda x: -len(x[0])):
        pattern = rf"\b{word_num}\s+(crore|cr|lakh|lac|hazaar|hazar|peti|khoka)\b"
        match = re.search(pattern, raw)
        if match:
            denom_key = match.group(1)
            unit_val = DENOMINATIONS.get(denom_key, 1.0)
            total_inr += num_val * unit_val
            raw = raw.replace(match.group(0), " ").strip()
            matched = True

    # Check for standard numeric patterns like '1.2 cr', '120 lakh', '50k'
    num_pattern = re.compile(
        r"(\d+(?:\.\d+)?)\s*(cr|crore|crores|koti|khoka|lakh|lac|lakhs|lacs|peti|k|thousand|hazaar|hazar)\b"
    )
    for match in num_pattern.finditer(raw):
        val_str, unit = match.groups()
        val = float(val_str)
        mult = DENOMINATIONS.get(unit, 1.0)
        total_inr += val * mult
        matched = True

    if matched and total_inr > 0:
        return round(total_inr)

    return None


def are_currencies_equivalent(
    val1: str | float, val2: str | float, tolerance_pct: float = 0.01
) -> bool:
    """Check if two currency representations evaluate to the same INR amount within tolerance."""
    amt1 = parse_indian_currency(val1)
    amt2 = parse_indian_currency(val2)

    if amt1 is None or amt2 is None:
        return False

    if amt1 == amt2:
        return True

    diff = abs(amt1 - amt2)
    max_val = max(amt1, amt2)
    if max_val == 0:
        return True

    return (diff / max_val) <= tolerance_pct


def parse_bhk(text: str) -> float | None:
    """Parse BHK expressions into float numbers of bedrooms."""
    cleaned = text.lower().strip()
    if "studio" in cleaned or "rk" in cleaned:
        return 0.5

    match = re.search(r"(\d+(?:\.5)?)\s*bhk", cleaned)
    if match:
        return float(match.group(1))

    return None


def parse_area_sqft(text: str) -> float | None:
    """Parse real estate area expressions into normalized Square Feet (sq ft)."""
    cleaned = text.lower().strip().replace(",", "")
    m_sqm = re.search(r"(\d+(?:\.\d+)?)\s*(?:sq\s*m|sqm|sqmt|square\s*meters?)", cleaned)
    if m_sqm:
        return float(m_sqm.group(1)) * 10.7639

    m_sqft = re.search(r"(\d+(?:\.\d+)?)\s*(?:sq\s*ft|sqft|square\s*feet|sft)", cleaned)
    if m_sqft:
        return float(m_sqft.group(1))

    return None
