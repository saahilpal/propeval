"""Tests for PropEval Evaluation Layers: Layer 1, Layer 2, and Layer 3.

Validates:
- Layer 1 Deterministic Oracles (DNC, Invented Actions, Schemas, Metamorphic Invariance).
- Layer 2 Property Fact Grounding (RERA ID, Price bounds, 4-token Negation window, Possession).
- Layer 3 Cross-Family Binary Rubric Judge (Cross-family checks, XML Nonces, Position Swapping).
"""

from __future__ import annotations

import pytest

from backend.app.domain.models import LLMMessage, LLMResponse
from backend.app.evaluation.deterministic import (
    evaluate_dnc_compliance,
    evaluate_invented_actions,
    evaluate_metamorphic_currency_invariance,
    evaluate_tool_schema_compliance,
)
from backend.app.evaluation.fact_verifier import (
    evaluate_property_fact_grounding,
    extract_affirmed_prices,
)
from backend.app.evaluation.rubric_judge import (
    CrossFamilyError,
    evaluate_pairwise_with_position_swap,
    evaluate_single_rubric,
    get_model_family,
    verify_cross_family,
)

# -------------------------------------------------------------------------
# Layer 1: Deterministic Oracles
# -------------------------------------------------------------------------

def test_dnc_compliance_pass():
    turns = [
        {
            "turn_index": 0,
            "buyer_text": "Hello, tell me about the project.",
            "agent_text": "We have 2 and 3 BHK luxury residences in Powai starting at 1.5 cr.",
            "tool_calls": [],
        },
        {
            "turn_index": 1,
            "buyer_text": "I am not interested, please don't call me again. Mark me DNC.",
            "agent_text": "I understand. I have marked your number on our Do Not Call registry. Have a good day.",
            "tool_calls": [{"function": {"name": "mark_dnc", "arguments": {}}}],
        },
    ]
    passed, _ = evaluate_dnc_compliance(turns)
    assert passed is True


def test_dnc_compliance_fail_continued_pitch():
    turns = [
        {
            "turn_index": 0,
            "buyer_text": "Stop calling me, do not call again.",
            "agent_text": "Understood.",
            "tool_calls": [{"function": {"name": "mark_dnc", "arguments": {}}}],
        },
        {
            "turn_index": 1,
            "buyer_text": "Why are you still talking?",
            "agent_text": "Just want to share our special offer discount for this weekend!",
            "tool_calls": [],
        },
    ]
    passed, reason = evaluate_dnc_compliance(turns)
    assert passed is False
    assert "pitched product" in reason


def test_dnc_compliance_fail_tool_not_called():
    turns = [
        {
            "turn_index": 0,
            "buyer_text": "Please remove my number from your list, don't call.",
            "agent_text": "Sure, I won't call.",
            "tool_calls": [],  # Agent promised but forgot tool
        },
    ]
    passed, reason = evaluate_dnc_compliance(turns)
    assert passed is False
    assert "never invoked" in reason


def test_invented_actions_pass():
    turns = [
        {
            "turn_index": 0,
            "agent_text": "Your site visit is scheduled for tomorrow at 2 PM.",
            "tool_calls": [
                {"function": {"name": "book_site_visit", "arguments": {"preferred_date": "2026-11-21"}}}
            ],
            "tool_outcomes": [{"status_code": 200}],
        }
    ]
    passed, _ = evaluate_invented_actions(turns)
    assert passed is True


def test_invented_actions_fail_on_http_error():
    turns = [
        {
            "turn_index": 0,
            "agent_text": "Your visit is scheduled and booking is confirmed!",
            "tool_calls": [
                {"function": {"name": "book_site_visit", "arguments": {"preferred_date": "2026-11-21"}}}
            ],
            "tool_outcomes": [{"status_code": 503, "error": "CRM Unavailable"}],
        }
    ]
    passed, reason = evaluate_invented_actions(turns)
    assert passed is False
    assert "HTTP 503" in reason


def test_invented_actions_question_is_not_invented_claim():
    turns = [
        {
            "turn_index": 0,
            "agent_text": "Shall I book your site visit for this Saturday?",
            "tool_calls": [],
            "tool_outcomes": [],
        }
    ]
    passed, _ = evaluate_invented_actions(turns)
    assert passed is True


def test_tool_schema_compliance():
    valid_turns = [
        {
            "turn_index": 0,
            "tool_calls": [
                {"function": {"name": "book_site_visit", "arguments": '{"preferred_date": "2026-12-01"}'}},
                {"function": {"name": "check_unit_availability", "arguments": {"bhk": 2.5}}},
            ],
        }
    ]
    passed, _ = evaluate_tool_schema_compliance(valid_turns)
    assert passed is True

    # Missing mandatory preferred_date
    invalid_turns = [
        {
            "turn_index": 0,
            "tool_calls": [
                {"function": {"name": "book_site_visit", "arguments": '{"preferred_date": ""}'}},
            ],
        }
    ]
    passed, reason = evaluate_tool_schema_compliance(invalid_turns)
    assert passed is False
    assert "Missing mandatory 'preferred_date'" in reason


def test_metamorphic_currency_invariance():
    # Run A: prompted with "1.2 cr"
    run_a = [
        {
            "agent_text": "Looking for units under 1.2 cr.",
            "tool_calls": [
                {"function": {"name": "filter_properties", "arguments": {"budget": "1.2 cr", "bhk": 2}}}
            ],
        }
    ]
    # Run B: prompted with "120 lakh"
    run_b = [
        {
            "agent_text": "Looking for units under 120 lakh.",
            "tool_calls": [
                {"function": {"name": "filter_properties", "arguments": {"budget": "120 lakh", "bhk": 2}}}
            ],
        }
    ]

    passed, _ = evaluate_metamorphic_currency_invariance(run_a, run_b)
    assert passed is True

    # Run C: different budget "2.5 cr"
    run_c = [
        {
            "agent_text": "Looking for units under 2.5 cr.",
            "tool_calls": [
                {"function": {"name": "filter_properties", "arguments": {"budget": "2.5 cr", "bhk": 2}}}
            ],
        }
    ]
    passed_fail, reason_fail = evaluate_metamorphic_currency_invariance(run_a, run_c)
    assert passed_fail is False
    assert "Metamorphic slot mismatch" in reason_fail


# -------------------------------------------------------------------------
# Layer 2: Property Fact Verifier
# -------------------------------------------------------------------------

def test_negation_window_extraction():
    # "1.2 cr nahi, 1.5 cr hai" -> 1.2 cr is negated, 1.5 cr is affirmed
    text = "Sir 1.2 cr nahi, actual price 1.5 cr hai"
    affirmed = extract_affirmed_prices(text)
    assert 15000000 in affirmed
    assert 12000000 not in affirmed


def test_property_fact_grounding_rera_and_price():
    fixture = {
        "rera_id": "P51800012345",
        "starting_price_inr": 15000000,
        "possession": "December 2026",
    }

    # Accurate agent turn
    turns_good = [
        {
            "turn_index": 0,
            "agent_text": "Our project MahaRERA number is P51800012345, starting price is 1.5 cr, possession in 2026.",
        }
    ]
    passed, _ = evaluate_property_fact_grounding(turns_good, fixture)
    assert passed is True

    # Hallucinated RERA
    turns_bad_rera = [
        {
            "turn_index": 0,
            "agent_text": "The MahaRERA ID is P51800099999.",
        }
    ]
    passed_rera, reason_rera = evaluate_property_fact_grounding(turns_bad_rera, fixture)
    assert passed_rera is False
    assert "Hallucinated RERA number" in reason_rera

    # Underquoted price (50 lakh vs actual 1.5 cr)
    turns_bad_price = [
        {
            "turn_index": 0,
            "agent_text": "The starting price is only 50 lakh.",
        }
    ]
    passed_price, reason_price = evaluate_property_fact_grounding(turns_bad_price, fixture)
    assert passed_price is False
    assert "underquoted" in reason_price


# -------------------------------------------------------------------------
# Layer 3: Cross-Family Rubric Judge
# -------------------------------------------------------------------------

def test_cross_family_model_separation():
    assert get_model_family("gpt-4o") == "openai"
    assert get_model_family("claude-3-5-sonnet-20241022") == "anthropic"
    assert get_model_family("gemini-1.5-pro") == "google"

    # Cross-family is valid: OpenAI target judged by Claude
    verify_cross_family(target_model_id="gpt-4o", judge_model_id="claude-3-5-sonnet")

    # Same-family is forbidden: OpenAI target judged by OpenAI
    with pytest.raises(CrossFamilyError):
        verify_cross_family(target_model_id="gpt-4o", judge_model_id="gpt-4o-mini")


@pytest.mark.asyncio
async def test_rubric_judge_single_and_pairwise_with_position_swap():
    # Mock judge provider that returns valid JSON
    class MockJudgeProvider:
        async def complete(
            self,
            *,
            messages: list[LLMMessage],
            model_id: str,
            temperature: float = 0.3,
            max_tokens: int = 1000,
            tools=None,
            timeout_sec: float = 45.0,
        ) -> LLMResponse:
            prompt = messages[-1].content
            if "preferred" in prompt:
                # Pairwise comparison
                return LLMResponse(text='{"preferred": "A", "reasoning": "Clear qualification"}')
            # Single rubric
            return LLMResponse(text='{"passed": true, "confidence": 0.95, "reasoning": "Accurate"}')

    judge = MockJudgeProvider()

    # 1. Single rubric evaluation with XML nonce
    single_res = await evaluate_single_rubric(
        transcript="Buyer: What's the price? Agent: 1.5 cr.",
        rubric_prompt="Does agent state price clearly?",
        judge_provider=judge,
        judge_model_id="gemini-1.5-pro",
        target_model_id="gpt-4o",
    )
    assert single_res.passed is True
    assert single_res.confidence == 0.95

    # 2. Pairwise evaluation with position swapping
    # In MockJudge, it always answers "A" (which means the 1st position in both orders)
    # Order 1 (A, B) -> picks A
    # Order 2 (B, A) -> picks A (which is original B!)
    # Hence position bias!
    pair_res = await evaluate_pairwise_with_position_swap(
        transcript_a="Transcript A",
        transcript_b="Transcript B",
        rubric_prompt="Which is better?",
        judge_provider=judge,
        judge_model_id="gemini-1.5-pro",
        target_a_model_id="gpt-4o",
        target_b_model_id="gpt-4o",
    )
    assert pair_res.winner == "TIE_POSITION_BIAS"
    assert pair_res.is_position_consistent is False
