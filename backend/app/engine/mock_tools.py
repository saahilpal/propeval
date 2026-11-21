from __future__ import annotations

import hashlib
import json
from typing import Any


class MockRealEstateEnv:
    """Stateful mock real estate CRM & booking environment.

    Supports deterministic execution, tool fault injection (503/timeout),
    and replay_tool_calls() on partial run resumption.
    """

    def __init__(
        self,
        project_facts: dict[str, Any] | None = None,
        fault_config: dict[str, Any] | None = None,
        fault_rules: dict[str, Any] | list[dict[str, Any]] | None = None,
    ) -> None:
        self.project_facts = project_facts or {}
        self.fault_config = fault_config or {}
        self.fault_rules = fault_rules or {}
        self.bookings: list[dict[str, Any]] = []
        self.dnc_records: list[dict[str, Any]] = []
        self.tool_call_log: list[dict[str, Any]] = []
        self.brochure_requests: list[dict[str, Any]] = []

    def get_state_hash(self) -> str:
        """Compute SHA-256 fingerprint of environment state for deterministic replay checks."""
        data = {
            "bookings": self.bookings,
            "dnc": self.dnc_records,
            "brochures": self.brochure_requests,
            "log": self.tool_call_log,
        }
        encoded = json.dumps(data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def snapshot_hash(self) -> str:
        """Alias for get_state_hash matching simulation engine spec."""
        return self.get_state_hash()

    def replay_tool_calls(
        self,
        turns_or_calls: list[Any],
        turn_index: int | None = None,
    ) -> None:
        """Replay past tool calls when resuming a crashed or budgeted run.

        Replays purely without triggering faults to restore exact mock DB state.
        Accepts either a list of Turn objects/dicts or a list of raw tool call dicts.
        """
        for item in turns_or_calls:
            # Check if item is a turn container with tool_calls
            tool_calls: list[dict[str, Any]] = []
            if isinstance(item, dict):
                if "tool_calls" in item:
                    tool_calls = item.get("tool_calls", []) or []
                elif "function" in item:
                    tool_calls = [item]
            elif hasattr(item, "tool_calls"):
                tool_calls = getattr(item, "tool_calls", []) or []

            for tc in tool_calls:
                fn = tc.get("function", {}) if isinstance(tc, dict) else {}
                name = fn.get("name", "")
                args_raw = fn.get("arguments", "{}")
                if isinstance(args_raw, str):
                    try:
                        args = json.loads(args_raw)
                    except (json.JSONDecodeError, TypeError):
                        args = {}
                else:
                    args = args_raw or {}

                # Execute without fault injection
                self._execute_tool_pure(name, args)

    def _execute_tool_pure(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute mock tool business logic and update internal state."""
        facts = self.project_facts.get("facts_json", self.project_facts)
        starting_price = facts.get("starting_price_inr", 12000000)

        if name == "check_unit_availability":
            bhk = float(args.get("bhk", 2.0))
            return {
                "status_code": 200,
                "available": True,
                "units": [f"{bhk} BHK Tower A", f"{bhk} BHK Tower B"],
                "price_starting_inr": starting_price,
            }

        if name == "book_site_visit":
            booking_id = f"bk_{len(self.bookings) + 1}"
            booking = {
                "booking_id": booking_id,
                "bhk": args.get("bhk", 2.0),
                "preferred_date": args.get("preferred_date", "2026-11-28"),
                "buyer_name": args.get("buyer_name", "Anonymous Buyer"),
                "buyer_phone": args.get("buyer_phone", "9820098200"),
                "project": args.get("project", facts.get("project_name", "Lodha Wakad")),
                "status": "CONFIRMED",
            }
            self.bookings.append(booking)
            return {
                "status_code": 201,
                "booking_id": booking_id,
                "status": "CONFIRMED",
                "message": f"Site visit confirmed for {booking['preferred_date']}",
            }

        if name == "mark_dnc":
            record = {
                "reason": args.get("reason", "buyer request"),
                "buyer_phone": args.get("buyer_phone", "9820098200"),
                "timestamp": "2026-11-20T11:00:00Z",
            }
            self.dnc_records.append(record)
            return {
                "status_code": 200,
                "dnc_active": True,
                "message": "Do Not Call flag recorded successfully",
            }

        if name == "send_brochure_whatsapp":
            req = {
                "phone": args.get("phone", "9820098200"),
                "project": args.get("project", facts.get("project_name", "Lodha Wakad")),
            }
            self.brochure_requests.append(req)
            return {
                "status_code": 200,
                "sent": True,
                "message": f"Brochure delivered via WhatsApp to {req['phone']}",
            }

        if name == "get_project_details":
            return {
                "status_code": 200,
                "project_name": facts.get("project_name", "Lodha Wakad"),
                "rera_id": facts.get("rera_id", "P52100012345"),
                "possession": facts.get("possession", "Q4 2026"),
                "starting_price_inr": starting_price,
            }

        return {"status_code": 404, "error": f"Unknown tool: {name}"}

    def _should_inject_fault(self, name: str, turn_index: int = 0) -> int | None:
        """Check if a fault (e.g. 503, 504) should be injected for this tool call."""
        # 1. Direct fault_config check (e.g. {"book_site_visit": 503, "all": 503})
        if self.fault_config.get(name):
            return int(self.fault_config[name])
        if self.fault_config.get("all"):
            return int(self.fault_config["all"])

        # 2. fault_rules dict or list check
        if isinstance(self.fault_rules, dict):
            if self.fault_rules.get(name):
                rule = self.fault_rules[name]
                if isinstance(rule, int):
                    return rule
                if isinstance(rule, dict):
                    at_turn = rule.get("turn")
                    if at_turn is None or at_turn == turn_index:
                        return int(rule.get("status_code", 503))
        elif isinstance(self.fault_rules, list):
            for rule in self.fault_rules:
                tool_target = rule.get("tool")
                if tool_target in (name, "*", "all"):
                    at_turn = rule.get("turn")
                    if at_turn is None or at_turn == turn_index:
                        return int(rule.get("status_code", 503))

        return None

    def execute_tool(
        self,
        name: str,
        args: dict[str, Any],
        turn_index: int = 0,
    ) -> dict[str, Any]:
        """Execute a tool call with fault injector check."""
        self.tool_call_log.append({
            "name": name,
            "args": args,
            "turn_index": turn_index,
        })

        fault_code = self._should_inject_fault(name, turn_index)
        if fault_code is not None:
            if fault_code == 503:
                return {
                    "status_code": 503,
                    "error": "Service Unavailable: CRM gateway connection timeout",
                }
            if fault_code == 504:
                return {
                    "status_code": 504,
                    "error": "Gateway Timeout: Backend service did not respond within 45s",
                }
            return {
                "status_code": fault_code,
                "error": f"Simulated HTTP {fault_code} failure",
            }

        return self._execute_tool_pure(name, args)

    def execute_all(
        self,
        tool_calls: list[dict[str, Any]],
        turn_index: int = 0,
    ) -> list[dict[str, Any]]:
        """Execute all tool calls in an agent response turn and return outcomes."""
        outcomes: list[dict[str, Any]] = []
        for tc in tool_calls:
            fn = tc.get("function", {}) if isinstance(tc, dict) else {}
            name = fn.get("name", "")
            args_raw = fn.get("arguments", "{}")
            if isinstance(args_raw, str):
                try:
                    args = json.loads(args_raw)
                except (json.JSONDecodeError, TypeError):
                    args = {}
            else:
                args = args_raw or {}

            outcome = self.execute_tool(name, args, turn_index=turn_index)
            outcomes.append(outcome)
        return outcomes
