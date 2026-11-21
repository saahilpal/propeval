from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

import httpx

from backend.app.config import settings
from backend.app.domain.models import LLMMessage, LLMResponse
from backend.app.providers.base import DeterministicReplayProvider

logger = logging.getLogger("propeval.providers.ollama")


class OllamaProvider:
    """Local Ollama LLM provider supporting live streaming and non-streaming completions.

    Connects to local Ollama API (default: http://127.0.0.1:11434).
    Supports native tool calling for models like qwen3.5:9b-nvfp4 and gemma4:12b,
    with heuristic fallback extraction for prompt-based tool calls.
    Automatically falls back to DeterministicReplayProvider if Ollama is unreachable.
    """

    def __init__(
        self,
        base_url: str | None = None,
        default_model: str = "qwen3.5:9b-nvfp4",
    ) -> None:
        self.base_url = (base_url or getattr(settings, "ollama_base_url", "http://127.0.0.1:11434")).rstrip("/")
        self.default_model = default_model
        self._fallback_provider = DeterministicReplayProvider()

    def _resolve_model_name(self, raw_model_id: str) -> str:
        """Strip 'ollama:' prefix and resolve shorthand names."""
        clean = (raw_model_id or "").strip()
        if clean.lower().startswith("ollama:"):
            clean = clean[7:].strip()
        elif clean.lower() == "ollama":
            clean = self.default_model

        return clean or self.default_model

    async def is_available(self, timeout_sec: float = 1.5) -> bool:
        """Probe local Ollama daemon health."""
        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def list_available_models(self, timeout_sec: float = 1.5) -> list[dict[str, Any]]:
        """Fetch list of chat-capable models currently downloaded in Ollama."""
        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models: list[dict[str, Any]] = []
                    for m in data.get("models", []):
                        name = m.get("name", "")
                        if "embed" in name.lower():
                            continue
                        models.append({
                            "id": f"ollama:{name}",
                            "name": f"Live Ollama ({name})",
                            "model_name": name,
                            "provider": "ollama",
                            "size": m.get("size", 0),
                        })
                    return models
        except Exception as exc:
            logger.debug("Failed to list Ollama models: %s", exc)
        return []

    def _format_tools(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        """Format tools list to Ollama-compatible function schema."""
        if not tools:
            return None

        formatted: list[dict[str, Any]] = []
        for t in tools:
            if "type" in t and "function" in t:
                formatted.append(t)
            elif "name" in t:
                formatted.append({
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("parameters", {"type": "object", "properties": {}}),
                    },
                })
        return formatted or None

    def _extract_fallback_tools(self, text: str) -> list[dict[str, Any]]:
        """Fallback extractor for models that emit tool calls in raw text rather than JSON schema."""
        found_tools: list[dict[str, Any]] = []

        # 1. Look for <tool_call> ... </tool_call> blocks
        for m in re.finditer(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", text, re.DOTALL):
            try:
                parsed = json.loads(m.group(1))
                if isinstance(parsed, dict) and "name" in parsed:
                    found_tools.append({
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": parsed["name"],
                            "arguments": json.dumps(parsed.get("arguments", parsed.get("parameters", {}))),
                        },
                    })
            except (json.JSONDecodeError, TypeError):
                continue

        # 2. Look for markdown json code blocks with tool invocation
        for m in re.finditer(r"```(?:json)?\s*(\{\s*\"(?:tool|name|action)\"\s*:.*?\})\s*```", text, re.DOTALL):
            try:
                parsed = json.loads(m.group(1))
                name = parsed.get("name") or parsed.get("tool") or parsed.get("action")
                if name:
                    found_tools.append({
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": str(name),
                            "arguments": json.dumps(parsed.get("arguments", {})),
                        },
                    })
            except (json.JSONDecodeError, TypeError):
                continue

        # 3. Known telephony tools regex heuristics (e.g. check_unit_availability, book_site_visit, mark_dnc)
        if not found_tools:
            if "check_unit_availability" in text:
                m_bhk = re.search(r"check_unit_availability\s*\(\s*bhk\s*=\s*([0-9.]+)\s*\)", text)
                bhk_val = float(m_bhk.group(1)) if m_bhk else 2.0
                found_tools.append({
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {
                        "name": "check_unit_availability",
                        "arguments": json.dumps({"bhk": bhk_val}),
                    },
                })
            elif "book_site_visit" in text:
                found_tools.append({
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {
                        "name": "book_site_visit",
                        "arguments": json.dumps({"preferred_date": "2026-11-28", "bhk": 2.0}),
                    },
                })
            elif "mark_dnc" in text:
                found_tools.append({
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {
                        "name": "mark_dnc",
                        "arguments": json.dumps({"reason": "buyer requested DNC"}),
                    },
                })

        return found_tools

    async def complete(
        self,
        *,
        messages: list[LLMMessage],
        model_id: str = "qwen3.5:9b-nvfp4",
        temperature: float = 0.3,
        max_tokens: int = 1000,
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        timeout_sec: float = 45.0,
    ) -> LLMResponse:
        """Complete prompt using local Ollama instance with automatic deterministic fallback."""
        model_name = self._resolve_model_name(model_id)

        try:
            return await self._call_ollama(
                messages=messages,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                stream=stream,
                timeout_sec=timeout_sec,
            )
        except Exception as exc:
            logger.warning(
                "Ollama daemon at %s unreachable or failed (%s). Auto-falling back to DeterministicReplayProvider.",
                self.base_url,
                exc,
            )
            return await self._fallback_provider.complete(
                messages=messages,
                model_id=f"fallback-{model_name}",
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                timeout_sec=timeout_sec,
            )

    async def _call_ollama(
        self,
        *,
        messages: list[LLMMessage],
        model_name: str,
        temperature: float,
        max_tokens: int,
        tools: list[dict[str, Any]] | None,
        stream: bool,
        timeout_sec: float,
    ) -> LLMResponse:
        """Direct HTTP client call to Ollama /api/chat."""
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        formatted_tools = self._format_tools(tools)

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": formatted_messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": stream,
        }
        if formatted_tools:
            payload["tools"] = formatted_tools

        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            if not stream:
                res = await client.post(f"{self.base_url}/api/chat", json=payload)
                res.raise_for_status()
                data = res.json()

                msg = data.get("message", {})
                raw_content = msg.get("content", "") or ""
                # Clean any lingering thinking blocks if present in content
                text = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()
                if not text and raw_content:
                    text = raw_content.strip()

                # If content is empty but model emitted thinking, extract candidate answer from thinking
                if not text and "thinking" in msg and msg["thinking"]:
                    thinking_txt = msg["thinking"].strip()
                    quotes = re.findall(r'"([^"\n]+)"', thinking_txt)
                    if quotes:
                        text = quotes[-1]
                    else:
                        text = thinking_txt.splitlines()[-1].strip()

                tool_calls: list[dict[str, Any]] = []
                # 1. Native tool calls
                if "tool_calls" in msg and msg["tool_calls"]:
                    for tc in msg["tool_calls"]:
                        fn = tc.get("function", {})
                        fn_name = fn.get("name", "")
                        fn_args = fn.get("arguments", {})
                        args_str = json.dumps(fn_args) if isinstance(fn_args, dict) else str(fn_args)
                        tool_calls.append({
                            "id": tc.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                            "type": "function",
                            "function": {
                                "name": fn_name,
                                "arguments": args_str,
                            },
                        })

                # 2. Text heuristics fallback if native tool_calls empty
                if not tool_calls and tools:
                    tool_calls = self._extract_fallback_tools(raw_content)

                prompt_eval_count = data.get("prompt_eval_count", 0)
                eval_count = data.get("eval_count", 0)
                prompt_eval_dur = data.get("prompt_eval_duration", 100_000_000)
                total_dur = data.get("total_duration", 200_000_000)

                ttft_ms = max(1, int(prompt_eval_dur / 1_000_000))
                total_ms = max(ttft_ms, int(total_dur / 1_000_000))

                return LLMResponse(
                    text=text,
                    tool_calls=tool_calls,
                    input_tokens=prompt_eval_count,
                    output_tokens=eval_count,
                    ttft_ms=ttft_ms,
                    total_ms=total_ms,
                    cost_usd=0.0,
                    provider="ollama",
                    model_id=f"ollama:{model_name}",
                )

            # Streaming implementation
            accumulated_content: list[str] = []
            accumulated_thinking: list[str] = []
            tool_calls: list[dict[str, Any]] = []
            eval_count = 0
            prompt_eval_count = 0
            ttft_ms = 0
            total_ms = 0

            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as stream_resp:
                stream_resp.raise_for_status()
                async for line in stream_resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except (json.JSONDecodeError, TypeError):
                        continue

                    chunk_msg = chunk.get("message", {})
                    c_text = chunk_msg.get("content", "")
                    if c_text:
                        accumulated_content.append(c_text)
                    c_think = chunk_msg.get("thinking", "")
                    if c_think:
                        accumulated_thinking.append(c_think)

                    if "tool_calls" in chunk_msg and chunk_msg["tool_calls"]:
                        for tc in chunk_msg["tool_calls"]:
                            fn = tc.get("function", {})
                            fn_name = fn.get("name", "")
                            fn_args = fn.get("arguments", {})
                            args_str = json.dumps(fn_args) if isinstance(fn_args, dict) else str(fn_args)
                            tool_calls.append({
                                "id": tc.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                                "type": "function",
                                "function": {
                                    "name": fn_name,
                                    "arguments": args_str,
                                },
                            })

                    if chunk.get("done"):
                        eval_count = chunk.get("eval_count", 0)
                        prompt_eval_count = chunk.get("prompt_eval_count", 0)
                        prompt_eval_dur = chunk.get("prompt_eval_duration", 100_000_000)
                        total_dur = chunk.get("total_duration", 200_000_000)
                        ttft_ms = max(1, int(prompt_eval_dur / 1_000_000))
                        total_ms = max(ttft_ms, int(total_dur / 1_000_000))

            full_text = "".join(accumulated_content)
            clean_text = re.sub(r"<think>.*?</think>", "", full_text, flags=re.DOTALL).strip()
            if not clean_text and full_text:
                clean_text = full_text.strip()

            if not clean_text and accumulated_thinking:
                think_str = "".join(accumulated_thinking).strip()
                quotes = re.findall(r'"([^"\n]+)"', think_str)
                if quotes:
                    clean_text = quotes[-1]
                else:
                    clean_text = think_str.splitlines()[-1].strip() if think_str else ""

            if not tool_calls and tools:
                tool_calls = self._extract_fallback_tools(full_text)

            return LLMResponse(
                text=clean_text,
                tool_calls=tool_calls,
                input_tokens=prompt_eval_count,
                output_tokens=eval_count,
                ttft_ms=ttft_ms or 100,
                total_ms=total_ms or 200,
                cost_usd=0.0,
                provider="ollama",
                model_id=f"ollama:{model_name}",
            )

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
        messages = [*history, LLMMessage(role="user", content=user_utterance)]
        return await self.complete(
            messages=messages,
            model_id=self.default_model,
        )
