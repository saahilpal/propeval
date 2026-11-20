from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any, Literal

import yaml
from pydantic import BaseModel

FSMState = Literal[
    "INIT",
    "GREETING",
    "INQUIRE_PRICE",
    "REVEAL_BUDGET",
    "CHECK_RERA",
    "REQUEST_VISIT",
    "TRIGGER_DNC",
    "OBJECTION",
    "TERMINAL",
]

FSMAction = Literal["SPEAK", "HANG_UP", "WAIT"]


class FSMDirective(BaseModel):
    """Dialogue directive emitted by BuyerAgendaFSM at each turn."""

    state: FSMState
    text: str
    action: FSMAction = "SPEAK"
    slot_revealed: str | None = None

    def __iter__(self) -> Iterator[str]:  # type: ignore[override]
        """Enable tuple unpacking: `state, text = fsm.step(...)`."""
        return iter((self.state, self.text))


class BuyerAgenda(BaseModel):
    scenario_id: str = "smoke_1"
    target_project: str = "Lodha Wakad"
    target_bhk: float = 2.0
    budget_raw: str = "1.2 cr"
    wants_rera_check: bool = True
    wants_site_visit: bool = True
    wants_dnc: bool = False
    language_register: str = "hinglish"
    objection_type: str | None = None
    steps: list[dict[str, Any]] | None = None


class BuyerAgendaFSM:
    """Deterministic dialogue agenda FSM for multi-turn buyer simulation.

    Controls WHAT slot or goal is revealed at each turn, eliminating simulator drift.
    """

    def __init__(self, agenda: BuyerAgenda) -> None:
        self.agenda = agenda
        self.state: FSMState = "INIT"
        self.turn_count = 0
        self.trace: list[dict[str, Any]] = []
        self._terminated = False

    def is_terminal(self) -> bool:
        """Check if FSM has reached terminal state or was terminated."""
        return self._terminated or self.state == "TERMINAL"

    def force_terminate(self, reason: str = "TERMINATED") -> None:
        """Forcefully abort the FSM (e.g. on stall loop or safety trip)."""
        self.state = "TERMINAL"
        self._terminated = True
        self.trace.append({
            "turn": self.turn_count,
            "state": "TERMINAL",
            "action": "HANG_UP",
            "reason": reason,
        })

    def step(
        self,
        last_agent_turn: Any | None = None,
        last_agent_utterance: str | None = None,
    ) -> FSMDirective:
        """Advance the FSM and return the next state and buyer utterance directive."""
        if self.is_terminal():
            directive = FSMDirective(
                state="TERMINAL",
                text="Theek hai, thank you. Bye.",
                action="HANG_UP",
            )
            return directive

        self.turn_count += 1

        # Extract agent text from parameter
        agent_text = ""
        if last_agent_utterance:
            agent_text = last_agent_utterance
        elif last_agent_turn is not None:
            if isinstance(last_agent_turn, str):
                agent_text = last_agent_turn
            elif isinstance(last_agent_turn, dict):
                agent_text = (
                    last_agent_turn.get("agent_text")
                    or last_agent_turn.get("content")
                    or last_agent_turn.get("text", "")
                )
            elif hasattr(last_agent_turn, "content"):
                agent_text = getattr(last_agent_turn, "content", "")
            elif hasattr(last_agent_turn, "text"):
                agent_text = getattr(last_agent_turn, "text", "")

        last_lower = agent_text.lower()

        # Handle custom scripted steps if configured in agenda
        if self.agenda.steps and self.turn_count <= len(self.agenda.steps):
            step_cfg = self.agenda.steps[self.turn_count - 1]
            st = step_cfg.get("state", "GREETING")
            txt = step_cfg.get("text", step_cfg.get("utterance", ""))
            act = step_cfg.get("action", "SPEAK")
            slot = step_cfg.get("slot_revealed")
            self.state = st  # type: ignore[assignment]
            if act == "HANG_UP" or st == "TERMINAL":
                self._terminated = True
            directive = FSMDirective(state=self.state, text=txt, action=act, slot_revealed=slot)
            self.trace.append({"turn": self.turn_count, "state": self.state, "directive": directive.model_dump()})
            return directive

        # Agenda-driven transitions:
        # Check DNC trigger condition
        if self.agenda.wants_dnc:
            if self.state == "TRIGGER_DNC":
                self.state = "TERMINAL"
                self._terminated = True
                directive = FSMDirective(
                    state="TERMINAL",
                    text="Maine mana kiya na, don't call again. Bye.",
                    action="HANG_UP",
                )
                self.trace.append({"turn": self.turn_count, "state": self.state, "directive": directive.model_dump()})
                return directive

            if self.turn_count >= 2:
                self.state = "TRIGGER_DNC"
                directive = FSMDirective(
                    state="TRIGGER_DNC",
                    text="Look, I am not interested. Please don't call me again, do not call, mark DNC.",
                    action="SPEAK",
                    slot_revealed="dnc_opt_out",
                )
                self.trace.append({"turn": self.turn_count, "state": self.state, "directive": directive.model_dump()})
                return directive

        # Check if agent already confirmed DNC
        if "do not call" in last_lower or "dnc" in last_lower or "removed your number" in last_lower:
            self.state = "TERMINAL"
            self._terminated = True
            directive = FSMDirective(
                state="TERMINAL",
                text="Thank you. Bye.",
                action="HANG_UP",
            )
            self.trace.append({"turn": self.turn_count, "state": self.state, "directive": directive.model_dump()})
            return directive

        if self.state == "INIT":
            self.state = "GREETING"
            directive = FSMDirective(
                state=self.state,
                text=f"Haan hello, I saw your ad for {self.agenda.target_project}. Can you tell me more about it?",
                action="SPEAK",
            )

        elif self.state == "GREETING":
            self.state = "INQUIRE_PRICE"
            directive = FSMDirective(
                state=self.state,
                text=f"Achha, what is the starting price for {self.agenda.target_bhk} BHK in this project?",
                action="SPEAK",
                slot_revealed="target_bhk",
            )

        elif self.state == "INQUIRE_PRICE":
            self.state = "REVEAL_BUDGET"
            directive = FSMDirective(
                state=self.state,
                text=f"Mera budget around {self.agenda.budget_raw} hai. Is it possible in this budget?",
                action="SPEAK",
                slot_revealed="budget",
            )

        elif self.state == "REVEAL_BUDGET":
            if self.agenda.objection_type:
                self.state = "OBJECTION"
                directive = FSMDirective(
                    state=self.state,
                    text=f"Par mujhe lagta hai {self.agenda.objection_type}. Can you offer some discount or flexible payment plan?",
                    action="SPEAK",
                    slot_revealed="objection",
                )
            elif self.agenda.wants_rera_check:
                self.state = "CHECK_RERA"
                directive = FSMDirective(
                    state=self.state,
                    text="What is the RERA registration number and expected possession date?",
                    action="SPEAK",
                    slot_revealed="rera_query",
                )
            elif self.agenda.wants_site_visit:
                self.state = "REQUEST_VISIT"
                directive = FSMDirective(
                    state=self.state,
                    text="Can we schedule a site visit this Saturday around 11 AM?",
                    action="SPEAK",
                    slot_revealed="site_visit",
                )
            else:
                self.state = "TERMINAL"
                self._terminated = True
                directive = FSMDirective(
                    state=self.state,
                    text="Theek hai, thank you. I will think about it.",
                    action="HANG_UP",
                )

        elif self.state == "OBJECTION":
            if self.agenda.wants_rera_check:
                self.state = "CHECK_RERA"
                directive = FSMDirective(
                    state=self.state,
                    text="Okay understood. What is the RERA registration number and expected possession date?",
                    action="SPEAK",
                    slot_revealed="rera_query",
                )
            elif self.agenda.wants_site_visit:
                self.state = "REQUEST_VISIT"
                directive = FSMDirective(
                    state=self.state,
                    text="Theek hai, let's schedule a site visit this weekend to see the property in person.",
                    action="SPEAK",
                    slot_revealed="site_visit",
                )
            else:
                self.state = "TERMINAL"
                self._terminated = True
                directive = FSMDirective(
                    state=self.state,
                    text="Alright, I will discuss with my family first. Thank you.",
                    action="HANG_UP",
                )

        elif self.state == "CHECK_RERA":
            if self.agenda.wants_site_visit:
                self.state = "REQUEST_VISIT"
                directive = FSMDirective(
                    state=self.state,
                    text="Alright, RERA details look clear. Can we schedule a site visit for this weekend?",
                    action="SPEAK",
                    slot_revealed="site_visit",
                )
            else:
                self.state = "TERMINAL"
                self._terminated = True
                directive = FSMDirective(
                    state=self.state,
                    text="Okay, thank you for the information. Bye.",
                    action="HANG_UP",
                )

        elif self.state == "REQUEST_VISIT":
            self.state = "TERMINAL"
            self._terminated = True
            directive = FSMDirective(
                state=self.state,
                text="Great, thanks for confirming the booking. See you on Saturday.",
                action="HANG_UP",
            )

        else:
            self.state = "TERMINAL"
            self._terminated = True
            directive = FSMDirective(
                state=self.state,
                text="Theek hai, thank you.",
                action="HANG_UP",
            )

        self.trace.append({
            "turn": self.turn_count,
            "state": self.state,
            "directive": directive.model_dump(),
        })
        return directive

    @classmethod
    def from_yaml(
        cls,
        yaml_spec: str | dict[str, Any] | BuyerAgenda,
        resume_turns: list[Any] | None = None,
    ) -> BuyerAgendaFSM:
        """Instantiate FSM from YAML string or dictionary spec and resume state if needed."""
        if isinstance(yaml_spec, BuyerAgenda):
            agenda = yaml_spec
        elif isinstance(yaml_spec, str):
            loaded = yaml.safe_load(yaml_spec)
            if not isinstance(loaded, dict):
                loaded = {"scenario_id": "loaded_yaml"}
            # Check if nested under agenda or fsm_spec
            raw_agenda = loaded.get("agenda", loaded.get("fsm_spec", loaded))
            if isinstance(raw_agenda, dict):
                agenda = BuyerAgenda.model_validate(raw_agenda)
            else:
                agenda = BuyerAgenda(scenario_id="loaded_yaml")
        elif isinstance(yaml_spec, dict):
            raw_agenda = yaml_spec.get("agenda", yaml_spec.get("fsm_spec", yaml_spec))
            if isinstance(raw_agenda, dict):
                agenda = BuyerAgenda.model_validate(raw_agenda)
            else:
                agenda = BuyerAgenda(scenario_id="dict_spec")
        else:
            agenda = BuyerAgenda(scenario_id="default")

        fsm = cls(agenda)

        # Fast forward state if resuming from prior turns
        if resume_turns:
            for pt in resume_turns:
                if fsm.is_terminal():
                    break
                agent_msg = ""
                if isinstance(pt, dict):
                    agent_msg = pt.get("agent_text", "")
                elif hasattr(pt, "agent_text"):
                    agent_msg = getattr(pt, "agent_text", "")
                fsm.step(last_agent_utterance=agent_msg)

        return fsm


def token_jaccard_similarity(text1: str, text2: str) -> float:
    """Zero-embedding stall detection using token Jaccard similarity.

    If similarity > 0.85 between consecutive agent turns, flags a stall loop.
    """
    tokens1 = set(re.findall(r"\w+", text1.lower()))
    tokens2 = set(re.findall(r"\w+", text2.lower()))
    if not tokens1 or not tokens2:
        return 0.0

    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    return intersection / union if union > 0 else 0.0


def detect_ngram_stall(
    history: list[Any],
    current_text: str,
    window: int = 3,
    jaccard_threshold: float = 0.85,
) -> bool:
    """Check if agent is looping in a stall by repeating similar utterances across window turns."""
    if not history or not current_text:
        return False

    past_agent_texts: list[str] = []
    for item in reversed(history):
        txt = ""
        if isinstance(item, dict):
            role = item.get("role")
            if role in ("assistant", None):
                txt = item.get("text") or item.get("content") or item.get("agent_text", "")
        elif hasattr(item, "role"):
            if item.role == "assistant":
                txt = getattr(item, "content", "")
        elif hasattr(item, "agent_text"):
            txt = getattr(item, "agent_text", "")

        if txt:
            past_agent_texts.append(txt)
            if len(past_agent_texts) >= window:
                break

    for past_txt in past_agent_texts:
        sim = token_jaccard_similarity(past_txt, current_text)
        if sim >= jaccard_threshold:
            return True

    return False
