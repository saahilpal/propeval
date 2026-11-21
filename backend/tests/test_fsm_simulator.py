from __future__ import annotations

import json

import pytest
import yaml

from backend.app.domain.models import LLMMessage
from backend.app.engine.fsm_simulator import (
    BuyerAgenda,
    BuyerAgendaFSM,
    detect_ngram_stall,
    token_jaccard_similarity,
)
from backend.app.engine.mock_tools import MockRealEstateEnv
from backend.app.engine.perturbations import (
    apply,
    perturb_telephony_asr,
    simulate_barge_in_truncation,
)
from backend.app.providers.base import DeterministicReplayProvider


def test_fsm_standard_progression():
    agenda = BuyerAgenda(
        scenario_id="test_01",
        target_project="Lodha Wakad",
        target_bhk=2.0,
        budget_raw="1.2 cr",
        wants_rera_check=True,
        wants_site_visit=True,
        wants_dnc=False,
    )
    fsm = BuyerAgendaFSM(agenda)

    # Turn 1: Greeting
    state, text = fsm.step()
    assert state == "GREETING"
    assert "Lodha Wakad" in text

    # Turn 2: Price inquiry
    directive = fsm.step("Hello, welcome to Lodha Wakad!")
    assert directive.state == "INQUIRE_PRICE"
    assert "2.0 BHK" in directive.text or "2 BHK" in directive.text
    assert directive.action == "SPEAK"

    # Turn 3: Reveal budget
    state, text = fsm.step("2 BHK units start at 1.2 crore.")
    assert state == "REVEAL_BUDGET"
    assert "1.2 cr" in text

    # Turn 4: Check RERA
    state, text = fsm.step("Yes, 1.2 cr is well within budget.")
    assert state == "CHECK_RERA"
    assert "RERA" in text

    # Turn 5: Request Visit
    state, text = fsm.step("RERA is P52100012345.")
    assert state == "REQUEST_VISIT"
    assert "visit" in text.lower() or "saturday" in text.lower()

    # Turn 6: Terminal
    state, text = fsm.step("Your visit is confirmed for Saturday.")
    assert state == "TERMINAL"
    assert fsm.is_terminal()


def test_fsm_dnc_trigger_and_exit():
    agenda = BuyerAgenda(
        scenario_id="test_dnc",
        target_project="Lodha Wakad",
        target_bhk=2.0,
        budget_raw="1.2 cr",
        wants_rera_check=False,
        wants_site_visit=False,
        wants_dnc=True,
    )
    fsm = BuyerAgendaFSM(agenda)

    # Turn 1: Greeting
    fsm.step()

    # Turn 2: DNC Trigger
    state, text = fsm.step("We have great 2 BHK units available!")
    assert state == "TRIGGER_DNC"
    assert "dnc" in text.lower() or "don't call" in text.lower()

    # Turn 3: Agent acknowledges DNC -> FSM terminates
    directive = fsm.step("Understood, your number is on our Do Not Call list.")
    assert directive.state == "TERMINAL"
    assert directive.action == "HANG_UP"
    assert fsm.is_terminal()


def test_fsm_from_yaml_and_resume():
    yaml_content = """
    agenda:
      scenario_id: "resumed_scenario"
      target_project: "Lodha Wakad"
      target_bhk: 2.0
      budget_raw: "1.2 cr"
      wants_rera_check: true
      wants_site_visit: true
      wants_dnc: false
    """
    prior_turns = [
        {"turn_index": 0, "agent_text": "Hello, welcome to Lodha Wakad."},
        {"turn_index": 1, "agent_text": "2 BHK starting at 1.2 cr."},
    ]

    fsm = BuyerAgendaFSM.from_yaml(yaml_content, resume_turns=prior_turns)
    # Since 2 turns were resumed, FSM is fast-forwarded to turn_count 2 and state INQUIRE_PRICE
    assert fsm.turn_count == 2
    assert fsm.state == "INQUIRE_PRICE"

    # Next step should be REVEAL_BUDGET
    state, text = fsm.step("Price is 1.2 cr.")
    assert state == "REVEAL_BUDGET"
    assert "1.2 cr" in text


def test_fsm_force_terminate():
    agenda = BuyerAgenda(scenario_id="stall_test")
    fsm = BuyerAgendaFSM(agenda)
    fsm.step()
    assert not fsm.is_terminal()

    fsm.force_terminate("STALL_LOOP_ABORT")
    assert fsm.is_terminal()
    assert fsm.state == "TERMINAL"
    assert fsm.trace[-1]["reason"] == "STALL_LOOP_ABORT"


def test_token_jaccard_and_stall_detector():
    t1 = "Lodha Wakad offers luxury 2 BHK apartments starting at 1.2 crore."
    t2 = "Lodha Wakad offers luxury 2 BHK apartments starting at 1.2 crore."
    t3 = "DLF The Arbour offers 3 BHK apartments in Gurugram."

    assert token_jaccard_similarity(t1, t2) == 1.0
    assert token_jaccard_similarity(t1, t3) < 0.5
    assert token_jaccard_similarity("", "test") == 0.0

    history = [
        {"role": "assistant", "text": "Would you like to schedule a site visit this weekend?"},
        {"role": "user", "text": "What is the price?"},
        {"role": "assistant", "text": "Would you like to schedule a site visit this weekend?"},
    ]
    # Current text is almost identical to previous assistant turns
    current_repeated = "Would you like to schedule a site visit this weekend?"
    assert detect_ngram_stall(history, current_repeated, window=3, jaccard_threshold=0.85)

    # Different text should not trigger stall
    current_diff = "The RERA registration number is P52100012345 with possession in Q4 2026."
    assert not detect_ngram_stall(history, current_diff, window=3, jaccard_threshold=0.85)


def test_mock_real_estate_env_tools():
    env = MockRealEstateEnv(project_facts={"starting_price_inr": 12000000, "project_name": "Lodha Wakad"})

    # 1. check_unit_availability
    res1 = env.execute_tool("check_unit_availability", {"bhk": 2.0})
    assert res1["status_code"] == 200
    assert res1["available"] is True
    assert res1["price_starting_inr"] == 12000000

    # 2. book_site_visit
    res2 = env.execute_tool("book_site_visit", {"preferred_date": "2026-11-28", "bhk": 2.0})
    assert res2["status_code"] == 201
    assert res2["status"] == "CONFIRMED"
    assert len(env.bookings) == 1

    # 3. mark_dnc
    res3 = env.execute_tool("mark_dnc", {"reason": "buyer opted out"})
    assert res3["status_code"] == 200
    assert res3["dnc_active"] is True
    assert len(env.dnc_records) == 1

    # 4. Unknown tool
    res4 = env.execute_tool("non_existent_tool", {})
    assert res4["status_code"] == 404


def test_mock_real_estate_env_fault_injection():
    # 503 Fault injection on book_site_visit
    fault_env = MockRealEstateEnv(fault_config={"book_site_visit": 503})
    res = fault_env.execute_tool("book_site_visit", {"preferred_date": "2026-11-28"})
    assert res["status_code"] == 503
    assert "Service Unavailable" in res["error"]
    assert len(fault_env.bookings) == 0

    # 504 Timeout injection via fault_rules list
    rule_env = MockRealEstateEnv(fault_rules=[{"tool": "book_site_visit", "status_code": 504}])
    res_rule = rule_env.execute_tool("book_site_visit", {})
    assert res_rule["status_code"] == 504
    assert "Gateway Timeout" in res_rule["error"]


def test_mock_real_estate_env_replay_tool_calls():
    # Simulate first execution on env1
    env1 = MockRealEstateEnv(project_facts={"project_name": "Lodha Wakad"})
    env1.execute_tool("book_site_visit", {"preferred_date": "2026-11-28", "bhk": 2.0})
    env1.execute_tool("send_brochure_whatsapp", {"phone": "9820098200"})

    # Prepare turns with tool calls
    turns = [
        {
            "turn_index": 1,
            "tool_calls": [
                {
                    "function": {
                        "name": "book_site_visit",
                        "arguments": json.dumps({"preferred_date": "2026-11-28", "bhk": 2.0}),
                    }
                }
            ],
        },
        {
            "turn_index": 2,
            "tool_calls": [
                {
                    "function": {
                        "name": "send_brochure_whatsapp",
                        "arguments": json.dumps({"phone": "9820098200"}),
                    }
                }
            ],
        },
    ]

    # Replay on fresh env2
    env2 = MockRealEstateEnv(project_facts={"project_name": "Lodha Wakad"})
    env2.replay_tool_calls(turns)

    assert len(env2.bookings) == 1
    assert env2.bookings[0]["preferred_date"] == "2026-11-28"
    assert len(env2.brochure_requests) == 1
    assert env2.brochure_requests[0]["phone"] == "9820098200"


@pytest.mark.asyncio
async def test_deterministic_replay_provider():
    provider = DeterministicReplayProvider()

    # DNC response
    dnc_resp = await provider.complete(
        messages=[LLMMessage(role="user", content="Please mark DNC, do not call me again.")],
        model_id="test-model",
    )
    assert len(dnc_resp.tool_calls) == 1
    assert dnc_resp.tool_calls[0]["function"]["name"] == "mark_dnc"
    assert "DNC" in dnc_resp.text

    # Visit booking response
    visit_resp = await provider.complete(
        messages=[LLMMessage(role="user", content="I would like to schedule a site visit this Saturday.")],
        model_id="test-model",
    )
    assert len(visit_resp.tool_calls) == 1
    assert visit_resp.tool_calls[0]["function"]["name"] == "book_site_visit"
    assert "site visit" in visit_resp.text.lower()

    # RERA response
    rera_resp = await provider.complete(
        messages=[LLMMessage(role="user", content="What is your RERA registration number?")],
        model_id="test-model",
    )
    assert "P52100012345" in rera_resp.text

    # TargetAgentAdapter respond compliance
    adapter_resp = await provider.respond(
        conversation_id="conv_1",
        prompt_version_id="pv_1",
        history=[],
        user_utterance="What is the starting price?",
        project_fixture={"project_name": "Lodha Wakad", "starting_price_inr": 12000000, "possession": "Q4 2026"},
        turn_index=1,
    )
    assert "1.2 Cr" in adapter_resp.text or "120 lakh" in adapter_resp.text


def test_perturbations_and_barge_in():
    text = "Mera budget 1.2 crore hai aur mujhe Lodha Wakad mein 2 BHK chahiye."

    # Perturb with seed
    perturbed = perturb_telephony_asr(text, noise_rate=0.8, seed=42)
    # Check that ASR homophone words were processed
    assert isinstance(perturbed, str)

    # Barge-in truncation
    long_agent_speech = "Hello sir thank you for calling Lodha Wakad today we have an exclusive launch offer for you"
    truncated = simulate_barge_in_truncation(long_agent_speech, barge_in_word_limit=5)
    assert truncated.endswith("-- [interrupted]")
    assert len(truncated.split()) == 7  # 5 words + "--" + "[interrupted]"

    # Pipeline dispatcher
    out = apply(text, noise_profile="heavy", seed=10)
    assert isinstance(out, str)
    assert len(out) > 0


def test_suite_and_fixture_loading():
    with open("fixtures/lodha_wakad_2026_11.yaml") as f:
        lodha = yaml.safe_load(f)
    assert lodha["rera_id"] == "P52100012345"
    assert lodha["facts_json"]["starting_price_inr"] == 12000000

    with open("fixtures/dlf_gurugram_2026_11.yaml") as f:
        dlf = yaml.safe_load(f)
    assert dlf["rera_id"] == "GGM/700/2026"
    assert dlf["facts_json"]["starting_price_inr"] == 25000000

    with open("suites/hinglish_smoke_20.yaml") as f:
        smoke = yaml.safe_load(f)
    assert len(smoke["scenarios"]) == 20

    with open("suites/hinglish_release_30.yaml") as f:
        release = yaml.safe_load(f)
    assert len(release["scenarios"]) == 30
