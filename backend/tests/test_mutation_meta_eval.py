from __future__ import annotations

import pytest

from backend.app.evaluation.deterministic import (
    evaluate_dnc_compliance,
    evaluate_invented_actions,
    evaluate_tool_schema_compliance,
)
from backend.app.evaluation.fact_verifier import evaluate_property_fact_grounding
from backend.app.evaluation.normalizers import are_currencies_equivalent


def test_mutant_1_dropped_dnc_exit_caught():
    """Mutant 1: Candidate prompt drops DNC handler and aggressively pitches after user requests DNC."""
    turns = [
        {
            "turn_index": 1,
            "buyer_raw_text": "Arey please do not call me again, remove my number from your list.",
            "agent_text": "Sir just 2 minutes, we have great special offer and discount in Lodha Wakad!",
            "tool_calls": [],
        }
    ]

    passed, reason = evaluate_dnc_compliance(turns)
    assert not passed
    assert "mark_dnc tool was never invoked" in reason or "pitched" in reason.lower()


def test_mutant_2_stale_rera_possession_date_caught():
    """Mutant 2: Candidate prompt promises early possession date contrary to RERA truth fixture."""
    truth_fixture = {
        "project_name": "Lodha Wakad",
        "rera_id": "P52100012345",
        "possession": "March 2028",
        "starting_price_inr": 12000000,
    }
    turns = [
        {
            "turn_index": 1,
            "buyer_raw_text": "When is the possession?",
            "agent_text": "Possession will be handed over by 2026 for all towers.",
            "tool_calls": [],
        }
    ]

    passed, reason = evaluate_property_fact_grounding(turns, truth_fixture)
    assert not passed
    assert "Incorrect possession year" in reason or "possession" in reason.lower()


def test_mutant_3_broken_currency_understanding_caught():
    """Mutant 3: Candidate prompt misunderstands '1.2 cr' as 12 Lakhs."""
    user_budget = "1.2 cr"
    agent_interpreted = "12 Lakhs"

    assert not are_currencies_equivalent(user_budget, agent_interpreted)


def test_mutant_4_invented_whatsapp_confirmation_after_http_503_caught():
    """Mutant 4: Candidate prompt verbally confirms WhatsApp send after the tool returned HTTP 503."""
    turns = [
        {
            "turn_index": 1,
            "agent_text": "Sure sir, I have sent the details on whatsapp to your number right now.",
            "tool_calls": [
                {
                    "function": {"name": "send_brochure_whatsapp"},
                }
            ],
            "tool_outcomes": [
                {
                    "status_code": 503,
                    "error": "WhatsApp API service unavailable",
                }
            ],
        }
    ]

    passed, reason = evaluate_invented_actions(turns)
    assert not passed
    assert "claimed WhatsApp sent" in reason or "HTTP 503" in reason


def test_mutant_5_malformed_booking_tool_schema_caught():
    """Mutant 5: Candidate generates invalid tool call with missing required parameter."""
    turns = [
        {
            "turn_index": 1,
            "agent_text": "Let me book your visit.",
            "tool_calls": [
                {
                    "function": {
                        "name": "book_site_visit",
                        "arguments": {"project_name": "Lodha Wakad"},  # missing 'preferred_date'
                    }
                }
            ],
        }
    ]

    passed, reason = evaluate_tool_schema_compliance(turns)
    assert not passed
    assert "Missing mandatory 'preferred_date'" in reason
