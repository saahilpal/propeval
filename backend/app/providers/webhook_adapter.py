from __future__ import annotations

import ipaddress
import json
import socket
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from backend.app.domain.models import LLMMessage, LLMResponse


class SSRFSecurityError(Exception):
    """Raised when an outbound URL violates SSRF safety boundaries."""
    pass


CGNAT_NET = ipaddress.ip_network("100.64.0.0/10")
METADATA_NET = ipaddress.ip_network("169.254.0.0/16")
MAX_RESPONSE_BYTES = 1_048_576  # 1 MB hard limit (docs/13 STRIDE DoS defense)


def is_ip_restricted(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if IP belongs to private, loopback, link-local, multicast, metadata, or CGNAT spaces."""
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return True

    # Explicit check for AWS/GCP/Azure link-local metadata and RFC 6598 CGNAT
    if isinstance(ip, ipaddress.IPv4Address):
        if ip in METADATA_NET or ip in CGNAT_NET:
            return True
        if str(ip) == "169.254.169.254":
            return True

    return False


def is_safe_webhook_url(url: str, enforce_https: bool = False) -> bool:
    """Validate that target URL does not point to loopback, link-local, multicast, or private IP spaces."""
    parsed = urlparse(url)
    allowed_schemes = ("https",) if enforce_https else ("http", "https")
    if parsed.scheme not in allowed_schemes:
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    # Block explicit localhost names and common bypass strings
    if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "[::1]"):
        return False

    try:
        # Resolve all IPs for hostname
        addr_info = socket.getaddrinfo(hostname, None)
        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip = ipaddress.ip_address(ip_str)
            if is_ip_restricted(ip):
                return False
        return True
    except (socket.gaierror, ValueError):
        return False


class RemoteWebhookAgentAdapter:
    """Safe outbound webhook adapter for customer real-estate voice agents under eval.

    Defenses enforced:
    - DNS resolution against private, loopback, link-local, CGNAT (100.64.0.0/10), and cloud metadata.
    - Zero-redirect enforcement (follow_redirects=False + explicit rejection of 3xx).
    - Strict timeouts: 5s connect, 30s read, 45s max wall-clock.
    - 1 MB streaming response size cap (prevents memory exhaustion / zip bombs).
    """

    def __init__(self, target_url: str, timeout_sec: float = 45.0, enforce_https: bool = False):
        if not is_safe_webhook_url(target_url, enforce_https=enforce_https):
            raise SSRFSecurityError(f"Target URL '{target_url}' resolved to a restricted IP address or loopback.")
        self.target_url = target_url
        self.enforce_https = enforce_https
        self.timeout_sec = min(timeout_sec, 45.0)  # Enforce 45s hard cap

    async def call_agent(self, payload: dict) -> dict:
        # Re-verify before each request (DNS rebinding protection)
        if not is_safe_webhook_url(self.target_url, enforce_https=self.enforce_https):
            raise SSRFSecurityError("Outbound request blocked by DNS rebinding guard.")

        # Structured timeouts: 5s connect, 30s read, 45s total
        timeout_config = httpx.Timeout(
            timeout=self.timeout_sec,
            connect=min(5.0, self.timeout_sec),
            read=min(30.0, self.timeout_sec),
            write=min(10.0, self.timeout_sec),
        )

        async with httpx.AsyncClient(timeout=timeout_config, follow_redirects=False) as client:
            async with client.stream("POST", self.target_url, json=payload) as resp:
                if resp.is_redirect:
                    loc = resp.headers.get("Location")
                    raise SSRFSecurityError(f"HTTP Redirect ({resp.status_code}) to '{loc}' rejected for security.")

                resp.raise_for_status()

                # Stream response up to 1 MB cap
                body_chunks: list[bytes] = []
                total_bytes = 0
                async for chunk in resp.aiter_bytes():
                    total_bytes += len(chunk)
                    if total_bytes > MAX_RESPONSE_BYTES:
                        raise SSRFSecurityError(
                            f"Response exceeded maximum allowed size of 1 MB ({total_bytes} bytes received)."
                        )
                    body_chunks.append(chunk)

                body_bytes = b"".join(body_chunks)
                return json.loads(body_bytes.decode("utf-8"))

    async def complete(
        self,
        *,
        messages: list[LLMMessage],
        model_id: str = "webhook",
        temperature: float = 0.3,
        max_tokens: int = 1000,
        tools: list[dict[str, Any]] | None = None,
        timeout_sec: float = 45.0,
    ) -> LLMResponse:
        """LLMProvider protocol implementation for outbound webhook."""
        t0 = time.perf_counter()
        payload = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "model_id": model_id,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tools": tools or [],
        }
        res_data = await self.call_agent(payload)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        # Standardize extracted agent text and tool calls
        text = res_data.get("text") or res_data.get("message") or res_data.get("content") or ""
        tool_calls = res_data.get("tool_calls", [])
        input_tokens = int(res_data.get("input_tokens", 0))
        output_tokens = int(res_data.get("output_tokens", 0))
        cost_usd = float(res_data.get("cost_usd", 0.0))
        ttft_ms = int(res_data.get("ttft_ms", min(elapsed_ms, 120)))
        total_ms = int(res_data.get("total_ms", elapsed_ms))

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            ttft_ms=ttft_ms,
            total_ms=total_ms,
            cost_usd=cost_usd,
            provider="webhook",
            model_id=model_id,
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
        """TargetAgentAdapter protocol compliance."""
        messages = [*history, LLMMessage(role="user", content=user_utterance)]
        return await self.complete(messages=messages, model_id=self.target_url)

    async def generate_turn(
        self,
        *,
        conversation_id: str,
        prompt_version_id: str,
        history: list[LLMMessage],
        user_utterance: str,
        project_fixture: dict[str, Any] | None = None,
        turn_index: int = 0,
    ) -> LLMResponse:
        """Alias for simulation turn generation."""
        return await self.respond(
            conversation_id=conversation_id,
            prompt_version_id=prompt_version_id,
            history=history,
            user_utterance=user_utterance,
            project_fixture=project_fixture or {},
            turn_index=turn_index,
        )

