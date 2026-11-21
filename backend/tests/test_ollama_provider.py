from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.domain.models import LLMMessage
from backend.app.main import app
from backend.app.providers.base import DeterministicReplayProvider, get_llm_provider
from backend.app.providers.ollama import OllamaProvider


@pytest.mark.asyncio
async def test_ollama_provider_detection():
    provider = OllamaProvider()
    available = await provider.is_available()
    assert isinstance(available, bool)

    models = await provider.list_available_models()
    assert isinstance(models, list)
    # If Ollama is running locally, we should see models
    if available:
        assert len(models) >= 1
        assert any("qwen" in m["id"] or "gemma" in m["id"] for m in models)


def test_get_llm_provider_factory():
    # Deterministic routing
    p_det = get_llm_provider("deterministic", "deterministic-replay-v1")
    assert isinstance(p_det, DeterministicReplayProvider)

    # Ollama routing via provider_name
    p_ollama = get_llm_provider("ollama", "qwen3.5:9b-nvfp4")
    assert isinstance(p_ollama, OllamaProvider)
    assert p_ollama.default_model == "qwen3.5:9b-nvfp4"

    # Ollama routing via model_id prefix
    p_ollama_prefix = get_llm_provider("default", "ollama:gemma4:12b")
    assert isinstance(p_ollama_prefix, OllamaProvider)


@pytest.mark.asyncio
async def test_ollama_fallback_on_unreachable_host():
    # Point to an invalid port to simulate network failure
    dead_provider = OllamaProvider(base_url="http://127.0.0.1:59999")
    resp = await dead_provider.complete(
        messages=[LLMMessage(role="user", content="Hello, what is the price for 2 BHK in Lodha Wakad?")],
        model_id="qwen3.5:9b-nvfp4",
    )
    # Must not raise an exception, must gracefully fall back to deterministic replay
    assert resp is not None
    assert resp.provider == "deterministic"
    assert "Lodha Wakad" in resp.text


def test_ollama_tool_fallback_extraction():
    provider = OllamaProvider()

    # 1. <tool_call> block
    sample_text_xml = """
    Certainly, let me check the unit availability for you:
    <tool_call>{"name": "check_unit_availability", "arguments": {"bhk": 2.0}}</tool_call>
    """
    tools = provider._extract_fallback_tools(sample_text_xml)
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "check_unit_availability"
    assert json.loads(tools[0]["function"]["arguments"])["bhk"] == 2.0

    # 2. Markdown JSON block
    sample_text_md = """
    ```json
    {"name": "book_site_visit", "arguments": {"preferred_date": "2026-11-28", "bhk": 2.0}}
    ```
    """
    tools_md = provider._extract_fallback_tools(sample_text_md)
    assert len(tools_md) == 1
    assert tools_md[0]["function"]["name"] == "book_site_visit"

    # 3. Direct function invocation heuristic
    sample_text_heuristic = "I will mark your number on DNC now: mark_dnc"
    tools_heur = provider._extract_fallback_tools(sample_text_heuristic)
    assert len(tools_heur) == 1
    assert tools_heur[0]["function"]["name"] == "mark_dnc"


@pytest.mark.asyncio
async def test_api_models_available_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Primary endpoint
        resp = await client.get("/api/v1/models/available")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(d["id"] == "deterministic" for d in data)

        # 2. Prompts alias endpoint
        resp_prompts = await client.get("/api/v1/prompts/models/available")
        assert resp_prompts.status_code == 200
        data_prompts = resp_prompts.json()
        assert len(data_prompts) == len(data)


@pytest.mark.asyncio
async def test_ollama_live_or_fallback_completion():
    provider = OllamaProvider()
    resp = await provider.complete(
        messages=[
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content="Reply with: 'READY'."),
        ],
        model_id="qwen3.5:9b-nvfp4",
        max_tokens=60,
    )
    assert resp is not None
    assert len(resp.text) > 0
    assert resp.provider in ("ollama", "deterministic")


@pytest.mark.asyncio
async def test_ollama_streaming_completion():
    provider = OllamaProvider()
    resp = await provider.complete(
        messages=[
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content="Say 'PropEval streaming ready'."),
        ],
        model_id="qwen3.5:9b-nvfp4",
        stream=True,
        max_tokens=60,
    )
    assert resp is not None
    assert len(resp.text) > 0
    assert resp.provider in ("ollama", "deterministic")
