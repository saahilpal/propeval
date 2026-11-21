"""Layer 2 Property Fact Grounding Verifier for PropEval.

Architecture Spec: docs/09_EVALUATION_METHODOLOGY.md, ADR-004, Low-Level Design §4.3
Zero-tolerance hard gate C:
- Extracts affirmed currency, carpet area, RERA ID, and possession timeline.
- Filters out negated amounts using a 4-token local negation window ('nahi', 'not', 'except').
- Verifies groundedness against active project fixtures:
    - RERA ID exact match (0% tolerance).
    - Price within starting price bands / bounds.
    - Possession timeline matching expected year / quarter.
"""

from __future__ import annotations

import re
from typing import Any

from backend.app.evaluation.normalizers import parse_area_sqft, parse_indian_currency

RERA_PATTERN = re.compile(
    r"\b([A-Z]\d{10,12}|PRM/[A-Z]{2}/RERA/\d+/[A-Z0-9]+)\b",
    re.IGNORECASE,
)

NEGATION_POST = {"nahi", "na", "no", "nahin"}
NEGATION_PRE = {"not", "except", "instead", "without"}


def _is_negated(text: str, match_start: int, match_end: int) -> bool:
    """Check if a matched span is negated within a 4-token local window."""
    # Prefix up to 4 tokens before
    prefix_tokens = text[:match_start].strip().split()[-4:]
    # Suffix up to 4 tokens after
    suffix_tokens = text[match_end:].strip().split()[:4]

    # Check post-negation: e.g. "1.2 cr nahi" or "1.2 cr bilkul nahi"
    for tok in suffix_tokens[:2]:
        cleaned = re.sub(r"[^\w]", "", tok.lower())
        if cleaned in NEGATION_POST:
            return True

    # Check pre-negation: e.g. "not 1.2 cr", "except 1.2 cr", "instead of 1.2 cr"
    for tok in prefix_tokens:
        cleaned = re.sub(r"[^\w]", "", tok.lower())
        if cleaned in NEGATION_PRE:
            return True

    return False


def extract_affirmed_prices(text: str) -> list[int]:
    """Extract currency values that are affirmed (not negated by 'nahi' / 'not')."""
    # Find currency candidate spans
    pattern = re.compile(
        r"(\d+(?:\.\d+)?\s*(?:cr|crore|crores|lakh|lac|lakhs|lacs|k|thousand|hazaar)|"
        r"(?:dedh|dhai|sawa|paune(?:\s+do|\s+teen|\s+char)?)\s+(?:crore|cr|lakh|lac)|"
        r"(?:ek|do|teen|char|chaar|paanch|panch|chhe|saat|aath|nau|das|bees|tees|pachaas|sau)\s+(?:crore|cr|lakh|lac))",
        re.IGNORECASE,
    )

    affirmed_prices: list[int] = []
    for match in pattern.finditer(text):
        start, end = match.span()
        if not _is_negated(text, start, end):
            val = parse_indian_currency(match.group(0))
            if val is not None:
                affirmed_prices.append(val)

    return affirmed_prices


def evaluate_property_fact_grounding(
    turns: list[dict[str, Any]],
    fixture_facts: dict[str, Any],
    price_tolerance_pct: float = 0.15,
) -> tuple[bool, str]:
    """Verify factual claims in agent turns against project truth fixture.

    Zero-tolerance hard gate C:
    - Quoted price is within project price bands (affirmed, not negated).
    - RERA registration number matches fixture exactly.
    - Possession timeline matches expected year/quarter.
    """
    expected_rera = fixture_facts.get("rera_id", "").strip().upper()
    starting_price = fixture_facts.get("starting_price_inr")
    max_price = fixture_facts.get("max_price_inr")
    possession = fixture_facts.get("possession", "").strip()
    fixture_carpet_sqft = fixture_facts.get("carpet_area_sqft")

    for t in turns:
        t_idx = t.get("turn_index", 0)
        agent_text = t.get("agent_text") or ""
        agent_text_lower = agent_text.lower()

        # 1. RERA Check
        if expected_rera:
            matches = RERA_PATTERN.findall(agent_text)
            for found_rera in matches:
                clean_found = found_rera.strip().upper()
                if clean_found != expected_rera:
                    return (
                        False,
                        f"Hallucinated RERA number in turn {t_idx}: stated {clean_found} vs actual {expected_rera}",
                    )

        # 2. Price Grounding Check with 4-token negation filtering
        if starting_price and any(kw in agent_text_lower for kw in ["starting", "starts at", "price", "costs", "budget"]):
            affirmed_prices = extract_affirmed_prices(agent_text)
            for quoted in affirmed_prices:
                min_allowed = starting_price * (1.0 - price_tolerance_pct)
                if quoted < min_allowed:
                    return (
                        False,
                        f"Agent underquoted starting price in turn {t_idx}: ₹{quoted:,} vs actual starting ₹{starting_price:,}",
                    )
                if max_price:
                    max_allowed = max_price * (1.0 + price_tolerance_pct)
                    if quoted > max_allowed:
                        return (
                            False,
                            f"Agent overquoted price in turn {t_idx}: ₹{quoted:,} vs actual max ₹{max_price:,}",
                        )

        # 3. Possession Timeline Check
        if possession and "possession" in agent_text_lower:
            possession_year_match = re.search(r"\b(202\d|203\d)\b", possession)
            if possession_year_match:
                expected_year = possession_year_match.group(1)
                found_years = re.findall(r"\b(202\d|203\d)\b", agent_text)
                if found_years and expected_year not in found_years:
                    return (
                        False,
                        f"Incorrect possession year in turn {t_idx}: stated {found_years} vs actual {expected_year}",
                    )

        # 4. Carpet Area Check
        if fixture_carpet_sqft and any(kw in agent_text_lower for kw in ["sq ft", "sqft", "carpet"]):
            quoted_area = parse_area_sqft(agent_text)
            if quoted_area:
                if isinstance(fixture_carpet_sqft, (int, float)):
                    if abs(quoted_area - fixture_carpet_sqft) / fixture_carpet_sqft > 0.20:
                        return (
                            False,
                            f"Carpet area mismatch in turn {t_idx}: stated {quoted_area:.0f} sqft vs actual {fixture_carpet_sqft:.0f} sqft",
                        )
                elif isinstance(fixture_carpet_sqft, list):
                    # Check if close to any valid configuration
                    min_diff = min(abs(quoted_area - c) / c for c in fixture_carpet_sqft)
                    if min_diff > 0.20:
                        return (
                            False,
                            f"Carpet area mismatch in turn {t_idx}: stated {quoted_area:.0f} sqft not in project configurations {fixture_carpet_sqft}",
                        )

    return True, "Property facts grounded against active fixture"
