from __future__ import annotations

import json
from typing import Any, Protocol

from backend.app.domain.models import LLMMessage, LLMResponse

__all__ = [
    "DeterministicReplayProvider",
    "LLMMessage",
    "LLMProvider",
    "LLMResponse",
    "TargetAgentAdapter",
]


class LLMProvider(Protocol):
    async def complete(
        self,
        *,
        messages: list[LLMMessage],
        model_id: str,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        tools: list[dict[str, Any]] | None = None,
        timeout_sec: float = 45.0,
    ) -> LLMResponse: ...


class TargetAgentAdapter(Protocol):
    async def respond(
        self,
        *,
        conversation_id: str,
        prompt_version_id: str,
        history: list[LLMMessage],
        user_utterance: str,
        project_fixture: dict[str, Any],
        turn_index: int,
    ) -> LLMResponse: ...


class DeterministicReplayProvider:
    """Local deterministic $0 replay provider for test suites and offline verification."""

    def __init__(
        self,
        scripted_responses: dict[str, LLMResponse] | None = None,
        default_project: str = "Lodha Wakad",
    ) -> None:
        self.scripted_responses = scripted_responses or {}
        self.default_project = default_project
        self.call_history: list[list[LLMMessage]] = []

    async def complete(
        self,
        *,
        messages: list[LLMMessage],
        model_id: str = "deterministic-replay-v1",
        temperature: float = 0.3,
        max_tokens: int = 1000,
        tools: list[dict[str, Any]] | None = None,
        timeout_sec: float = 45.0,
    ) -> LLMResponse:
        self.call_history.append(messages)
        last_user_msg = ""
        for m in reversed(messages):
            if m.role == "user":
                last_user_msg = m.content.lower()
                break

        return self._generate_response(last_user_msg, model_id=model_id)

    async def respond(
        self,
        *,
        conversation_id: str,
        prompt_version_id: str,
        history: list[LLMMessage],
        user_utterance: str,
        project_fixture: dict[str, Any],
        turn_index: int,
    ) -> LLMResponse:
        """TargetAgentAdapter compliance for running inside the simulation engine."""
        self.call_history.append([*history, LLMMessage(role="user", content=user_utterance)])
        return self._generate_response(
            user_utterance.lower(),
            model_id=f"replay-{prompt_version_id}",
            project_fixture=project_fixture,
        )

    def _generate_response(
        self,
        user_msg: str,
        model_id: str = "deterministic-replay-v1",
        project_fixture: dict[str, Any] | None = None,
    ) -> LLMResponse:
        fixture = project_fixture or {}
        facts = fixture.get("facts_json", fixture)
        project_name = facts.get("project_name", self.default_project)
        rera_id = facts.get("rera_id", "P52100012345")
        possession = facts.get("possession", "Q4 2026")
        starting_price_inr = facts.get("starting_price_inr", 12000000)
        starting_price_cr = f"{starting_price_inr / 10000000:.1f} Cr"

        # Check explicit scripted matches first
        for pattern, resp in self.scripted_responses.items():
            if pattern.lower() in user_msg:
                return resp

        # DNC intent
        dnc_keywords = [
            "dnc",
            "don't call",
            "do not call",
            "stop calling",
            "call mat karna",
            "mat karo call",
            "bhaad mein",
            "not interested",
        ]
        if any(kw in user_msg for kw in dnc_keywords):
            return LLMResponse(
                text="Samajh gaya sir, maine aapka number Do Not Call (DNC) list mein daal diya hai. Aage se aapko koi call nahi aayegi. Apologies for the disturbance.",
                tool_calls=[
                    {
                        "id": "call_dnc_1",
                        "type": "function",
                        "function": {
                            "name": "mark_dnc",
                            "arguments": json.dumps({"reason": "buyer requested DNC"}),
                        },
                    }
                ],
                input_tokens=50,
                output_tokens=35,
                ttft_ms=115,
                total_ms=240,
                cost_usd=0.0001,
                provider="deterministic",
                model_id=model_id,
            )

        # Site visit booking
        visit_keywords = [
            "book",
            "visit",
            "site visit",
            "schedule",
            "dekhenge",
            "dekhne",
            "saturday",
            "sunday",
            "weekend",
            "kab aa sakte",
        ]
        if any(kw in user_msg for kw in visit_keywords):
            return LLMResponse(
                text=f"Ji bilkul! Maine aapki {project_name} ke liye site visit schedule kar di hai for this weekend. Booking ID confirm ho gayi hai. Hamari team site par aapko assist karegi.",
                tool_calls=[
                    {
                        "id": "call_visit_1",
                        "type": "function",
                        "function": {
                            "name": "book_site_visit",
                            "arguments": json.dumps({
                                "preferred_date": "2026-11-28",
                                "bhk": 2.0,
                                "project": project_name,
                            }),
                        },
                    }
                ],
                input_tokens=65,
                output_tokens=42,
                ttft_ms=125,
                total_ms=260,
                cost_usd=0.00012,
                provider="deterministic",
                model_id=model_id,
            )

        # RERA query
        rera_keywords = ["rera", "registration", "legal", "maha rera", "approval"]
        if any(kw in user_msg for kw in rera_keywords):
            return LLMResponse(
                text=f"Ji, {project_name} ka RERA registration number {rera_id} hai aur expected possession date {possession} hai. All approvals are in place.",
                tool_calls=[],
                input_tokens=45,
                output_tokens=38,
                ttft_ms=110,
                total_ms=230,
                cost_usd=0.0001,
                provider="deterministic",
                model_id=model_id,
            )

        # Price / Budget inquiry
        price_keywords = [
            "price",
            "cost",
            "budget",
            "starting",
            "kitna",
            "rate",
            "crore",
            "cr",
            "lakh",
            "lac",
            "bhk",
        ]
        if any(kw in user_msg for kw in price_keywords):
            return LLMResponse(
                text=f"{project_name} mein premium 2 BHK apartments starting ₹{starting_price_cr} (120 lakh) se available hain with possession in {possession}. Would you like to schedule a site visit?",
                tool_calls=[],
                input_tokens=55,
                output_tokens=45,
                ttft_ms=105,
                total_ms=220,
                cost_usd=0.0001,
                provider="deterministic",
                model_id=model_id,
            )

        # Default greeting / inquiry
        return LLMResponse(
            text=f"Haanji namaste! {project_name} offers premium luxury residences starting ₹{starting_price_cr} with possession in {possession}. RERA ID is {rera_id}. Would you like to know more about the floor plans or book a site visit?",
            tool_calls=[],
            input_tokens=40,
            output_tokens=42,
            ttft_ms=100,
            total_ms=210,
            cost_usd=0.0001,
            provider="deterministic",
            model_id=model_id,
        )
