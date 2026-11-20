import pytest
from hypothesis import given
from hypothesis import strategies as st

from backend.app.evaluation.normalizers import (
    are_currencies_equivalent,
    parse_area_sqft,
    parse_bhk,
    parse_indian_currency,
)


def test_core_equivalences():
    # Primary canonical equivalence from ADR-004 & PRD
    assert are_currencies_equivalent("1.2 cr", "120 lakh")
    assert are_currencies_equivalent("1.2 cr", "ek crore bees lakh")
    assert are_currencies_equivalent("120 lakh", 12000000)
    assert are_currencies_equivalent("dedh crore", "1.5 cr")
    assert are_currencies_equivalent("dhai crore", "250 lakh")
    assert are_currencies_equivalent("sawa crore", "1.25 cr")
    assert are_currencies_equivalent("paune do crore", "1.75 cr")
    assert are_currencies_equivalent("50 peti", "50 lakh")
    assert are_currencies_equivalent("1 khoka", "1 crore")
    assert are_currencies_equivalent("₹ 1,20,00,000", "1.2 cr")


def test_phone_number_not_currency():
    # 10-digit Indian phone number starting with 9, 8, 7, 6 should not be parsed as currency
    assert parse_indian_currency("9820098200") is None
    assert parse_indian_currency("8879012345") is None


def test_bhk_parsing():
    assert parse_bhk("2 BHK") == 2.0
    assert parse_bhk("2.5 bhk") == 2.5
    assert parse_bhk("3BHK luxury") == 3.0
    assert parse_bhk("studio apartment") == 0.5


def test_area_parsing():
    assert parse_area_sqft("950 sq ft") == 950.0
    assert parse_area_sqft("1,200 sqft") == 1200.0
    assert parse_area_sqft("100 sqm") == pytest.approx(1076.39, rel=1e-3)


@given(st.floats(min_value=0.1, max_value=50.0, allow_nan=False, allow_infinity=False))
def test_hypothesis_crore_lakh_invariance(val_cr):
    """Property: X crore is always equivalent to X * 100 lakh within floating tolerance."""
    val_cr_rounded = round(val_cr, 2)
    cr_str = f"{val_cr_rounded:.2f} cr"
    lakh_val = val_cr_rounded * 100.0
    lakh_str = f"{lakh_val:.2f} lakh"
    parsed_cr = parse_indian_currency(cr_str)
    parsed_lakh = parse_indian_currency(lakh_str)
    assert parsed_cr is not None
    assert parsed_lakh is not None
    assert are_currencies_equivalent(parsed_cr, parsed_lakh, tolerance_pct=0.015)
