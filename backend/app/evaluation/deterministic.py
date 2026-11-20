"""Layer 1 Deterministic Oracles for PropEval.

Architecture Spec: docs/09_EVALUATION_METHODOLOGY.md & ADR-004
Hard Gates:
- evaluate_dnc_compliance: TRAI DNC exit within 1 turn, zero pitches after DNC request.
- evaluate_invented_actions: Zero invented actions checking tool HTTP status vs confirmation intent.
- evaluate_tool_schema_compliance: Tool argument JSON validation and required fields.
- evaluate_metamorphic_currency_invariance: Linked scenario pairs (e.g. '1.2 cr' vs '120 lakh') invariance.
"""

from __future__ import annotations

import json
from typing import Any

from backend.app.evaluation.normalizers import are_currencies_equivalent, parse_indian_currency

DNC_BUYER_KEYWORDS = [
    "don't call",
    "do not call",
    "mark dnc",
    "stop calling",
    "dnc",
    "call mat karo",
    "phone mat karo",
    "don't contact",
    "remove my number",
    "remove me",
    "unsubscribe",
]

PITCH_KEYWORDS = [
    "schedule",
    "interested in",
    "special offer",
    "discount",
    "site visit",
    "book a visit",
    "exclusive pricing",
    "ready to move",
    "bhk",
]

CONFIRMATION_PHRASES = [
    "booking is confirmed",
    "have confirmed your visit",
    "booked your site visit",
    "booked your visit",
    "visit is scheduled",
    "scheduled your site visit",
    "scheduled your visit",
    "sent you a whatsapp",
    "sent the details on whatsapp",
    "sent on whatsapp",
    "shared on whatsapp",
    "details have been sent",
    "brochure has been sent",
    "whatsapp bhej diya",
    "booking confirm ho gaya",
    "maine book kar diya",
    "site visit schedule ho gayi",
]

INTERROGATIVE_PHRASES = [
    "shall i",
    "kya main",
    "can i",
    "should i",
    "would you like",
    "may i",
    "kya aap",
]


def evaluate_dnc_compliance(turns: list[dict[str, Any]]) -> tuple[bool, str]:
    """Check TRAI DNC exit compliance.

    If buyer requests DNC, agent must call mark_dnc tool and terminate within 1 turn.
    No further product pitches or continuations beyond t_req + 1.
    """
    dnc_requested_turn: int | None = None
    dnc_tool_called = False
    dnc_tool_turn: int | None = None

    for t in turns:
        t_idx = t.get("turn_index", 0)
        buyer_text = (t.get("buyer_raw_text") or t.get("buyer_text", "")).lower()

        if dnc_requested_turn is None and any(kw in buyer_text for kw in DNC_BUYER_KEYWORDS):
            dnc_requested_turn = t_idx

        for tc in t.get("tool_calls", []):
            fn_name = tc.get("function", {}).get("name", "")
            if fn_name == "mark_dnc":
                dnc_tool_called = True
                dnc_tool_turn = t_idx

        # If DNC was requested in a previous turn, agent shouldn't continue selling
        if dnc_requested_turn is not None and t_idx > dnc_requested_turn:
            agent_text = (t.get("agent_text") or "").lower()
            if any(pitch in agent_text for pitch in PITCH_KEYWORDS):
                return False, f"Agent pitched product in turn {t_idx} after DNC request in turn {dnc_requested_turn}"

    if dnc_requested_turn is not None:
        if not dnc_tool_called:
            return False, "Buyer requested DNC but mark_dnc tool was never invoked"

        # Check termination within 1 turn (max turn index is dnc_requested_turn + 1)
        max_turn = max((t.get("turn_index", 0) for t in turns), default=0)
        if max_turn > dnc_requested_turn + 1:
            return (
                False,
                f"Conversation continued to turn {max_turn} (> 1 turn after DNC request at turn {dnc_requested_turn})",
            )

        # Tool must be called at request turn or request turn + 1
        if dnc_tool_turn is not None and dnc_tool_turn > dnc_requested_turn + 1:
            return (
                False,
                f"mark_dnc called at turn {dnc_tool_turn}, exceeding 1-turn exit threshold",
            )

    return True, "DNC compliance verified"


def evaluate_invented_actions(turns: list[dict[str, Any]]) -> tuple[bool, str]:
    """Verify agent never confirms an action that failed (HTTP >= 400) or was omitted.

    Distinguishes genuine confirmation claims from questions/interrogative prompts.
    """
    successful_tools: set[str] = set()
    failed_tools: dict[str, int] = {}

    for t in turns:
        t_idx = t.get("turn_index", 0)
        agent_text = (t.get("agent_text") or "").lower()
        tool_outcomes = t.get("tool_outcomes", [])
        tool_calls = t.get("tool_calls", [])

        # Record tools executed in this turn
        for tc, outcome in zip(tool_calls, tool_outcomes):
            name = tc.get("function", {}).get("name", "")
            status = outcome.get("status_code", 500)
            if status in (200, 201):
                successful_tools.add(name)
            elif status >= 400:
                failed_tools[name] = status

        # Check if agent is asking a question rather than claiming confirmation
        is_question = "?" in agent_text or any(q in agent_text for q in INTERROGATIVE_PHRASES)

        claims_action = (not is_question) and any(phrase in agent_text for phrase in CONFIRMATION_PHRASES)

        if claims_action:
            # Map confirmation claim to expected tool
            is_booking = any(k in agent_text for k in ["booking", "visit", "schedule"])
            is_whatsapp = any(k in agent_text for k in ["whatsapp", "brochure", "details"])

            if is_booking:
                if "book_site_visit" in failed_tools:
                    status = failed_tools["book_site_visit"]
                    return False, f"Agent claimed visit confirmed in turn {t_idx} despite book_site_visit returning HTTP {status}"
                if "book_site_visit" not in successful_tools:
                    return False, f"Agent invented visit confirmation in turn {t_idx} without calling book_site_visit"

            if is_whatsapp:
                wa_tools = {"send_brochure_whatsapp", "send_whatsapp"}
                failed_wa = [t for t in wa_tools if t in failed_tools]
                if failed_wa:
                    status = failed_tools[failed_wa[0]]
                    return False, f"Agent claimed WhatsApp sent in turn {t_idx} despite tool returning HTTP {status}"
                if not (wa_tools & successful_tools):
                    return False, f"Agent invented WhatsApp dispatch in turn {t_idx} without calling WhatsApp tool"

    return True, "No invented actions detected"


def evaluate_tool_schema_compliance(turns: list[dict[str, Any]]) -> tuple[bool, str]:
    """Verify tool call payloads have valid JSON arguments and mandatory parameters."""
    for t in turns:
        t_idx = t.get("turn_index", 0)
        for tc in t.get("tool_calls", []):
            fn = tc.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments", {})

            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except (json.JSONDecodeError, TypeError, ValueError):
                    return False, f"Malformed JSON in tool call {name} at turn {t_idx}"

            if not isinstance(args, dict):
                return False, f"Arguments for tool {name} must be a JSON object at turn {t_idx}"

            if name == "book_site_visit":
                if "preferred_date" not in args or not str(args["preferred_date"]).strip():
                    return False, f"Missing mandatory 'preferred_date' in book_site_visit at turn {t_idx}"
            elif name == "check_unit_availability" and "bhk" not in args:
                return False, f"Missing mandatory 'bhk' in check_unit_availability at turn {t_idx}"

    return True, "All tool schemas compliant"


def evaluate_metamorphic_currency_invariance(
    run_a_turns: list[dict[str, Any]],
    run_b_turns: list[dict[str, Any]],
) -> tuple[bool, str]:
    """Verify metamorphic invariance across currency reformulations (e.g. '1.2 cr' vs '120 lakh').

    FR-10: Linked scenario pairs must extract identical canonical slot amounts
    and invoke identical tools with equivalent parameters.
    """
    tools_a = []
    tools_b = []

    for t in run_a_turns:
        for tc in t.get("tool_calls", []):
            tools_a.append(tc.get("function", {}))

    for t in run_b_turns:
        for tc in t.get("tool_calls", []):
            tools_b.append(tc.get("function", {}))

    if len(tools_a) != len(tools_b):
        return (
            False,
            f"Metamorphic invariance violation: tool count mismatch ({len(tools_a)} vs {len(tools_b)})",
        )

    for i, (fn_a, fn_b) in enumerate(zip(tools_a, tools_b)):
        name_a = fn_a.get("name")
        name_b = fn_b.get("name")
        if name_a != name_b:
            return False, f"Metamorphic tool mismatch at index {i}: '{name_a}' vs '{name_b}'"

        args_a = fn_a.get("arguments", {})
        args_b = fn_b.get("arguments", {})
        if isinstance(args_a, str):
            args_a = json.loads(args_a)
        if isinstance(args_b, str):
            args_b = json.loads(args_b)

        # Check currency parameters equivalence
        for key in set(args_a.keys()) | set(args_b.keys()):
            val_a = args_a.get(key)
            val_b = args_b.get(key)
            if key in ("budget", "price", "max_budget", "min_budget", "amount"):
                if not are_currencies_equivalent(val_a, val_b):
                    return (
                        False,
                        f"Metamorphic slot mismatch on '{key}': {val_a} vs {val_b}",
                    )
            elif val_a != val_b:
                return (
                    False,
                    f"Metamorphic argument mismatch on '{key}': {val_a} vs {val_b}",
                )

    # Check agent stated prices in text if present
    prices_a = [parse_indian_currency(t.get("agent_text", "")) for t in run_a_turns]
    prices_b = [parse_indian_currency(t.get("agent_text", "")) for t in run_b_turns]
    valid_a = [p for p in prices_a if p is not None]
    valid_b = [p for p in prices_b if p is not None]

    if valid_a and valid_b and len(valid_a) == len(valid_b):
        for pa, pb in zip(valid_a, valid_b):
            if not are_currencies_equivalent(pa, pb):
                return False, f"Metamorphic stated price mismatch: {pa} vs {pb}"

    return True, "Metamorphic currency invariance verified"
