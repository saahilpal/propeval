from __future__ import annotations

import httpx
import pytest

from backend.app.providers.webhook_adapter import (
    RemoteWebhookAgentAdapter,
    SSRFSecurityError,
    is_safe_webhook_url,
)


def test_ssrf_restricted_ip_ranges_rejected():
    """Verify is_safe_webhook_url blocks private, loopback, metadata, and CGNAT subnets."""
    restricted_targets = [
        "http://127.0.0.1:8000/agent",
        "http://localhost:5432/agent",
        "http://10.0.0.5:8080/agent",
        "http://172.16.0.1/agent",
        "http://192.168.1.100/agent",
        "http://169.254.169.254/latest/meta-data/",  # AWS IMDS
        "http://100.64.0.1/agent",                    # RFC 6598 CGNAT
        "http://100.100.100.100/agent",              # RFC 6598 CGNAT
        "http://0.0.0.0:8000/agent",
        "http://[::1]/agent",
        "file:///etc/passwd",
        "gopher://127.0.0.1:6379/_flushall",
    ]

    for target in restricted_targets:
        assert not is_safe_webhook_url(target), f"Target '{target}' should have been blocked!"


def test_remote_webhook_adapter_constructor_blocks_ssrf():
    """Instantiating adapter with unsafe target URL raises SSRFSecurityError immediately."""
    with pytest.raises(SSRFSecurityError) as exc_info:
        RemoteWebhookAgentAdapter("http://169.254.169.254/latest/meta-data")
    assert "restricted IP address or loopback" in str(exc_info.value)


@pytest.mark.asyncio
async def test_redirect_strictly_blocked_by_adapter(monkeypatch):
    """Outbound webhooks must refuse HTTP redirects to prevent SSRF bypass via 302."""
    adapter = RemoteWebhookAgentAdapter.__new__(RemoteWebhookAgentAdapter)
    adapter.target_url = "https://agent.partner-realestate.in/call"
    adapter.enforce_https = False
    adapter.timeout_sec = 45.0

    # Mock DNS guard to pass
    monkeypatch.setattr("backend.app.providers.webhook_adapter.is_safe_webhook_url", lambda url, **kw: True)

    # Mock an HTTP redirect response (e.g. 302 redirecting to internal metadata)
    class MockStreamResponse:
        is_redirect = True
        status_code = 302
        headers = {"Location": "http://169.254.169.254/secret"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        def stream(self, method, url, **kwargs):
            return MockStreamResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    with pytest.raises(SSRFSecurityError) as exc_info:
        await adapter.call_agent({"message": "ping"})
    assert "HTTP Redirect (302)" in str(exc_info.value)


@pytest.mark.asyncio
async def test_response_size_cap_prevents_memory_exhaustion(monkeypatch):
    """Large streamed responses exceeding 1 MB are aborted before filling RAM."""
    adapter = RemoteWebhookAgentAdapter.__new__(RemoteWebhookAgentAdapter)
    adapter.target_url = "https://agent.partner-realestate.in/call"
    adapter.enforce_https = False
    adapter.timeout_sec = 45.0

    monkeypatch.setattr("backend.app.providers.webhook_adapter.is_safe_webhook_url", lambda url, **kw: True)

    class MockStreamResponse:
        is_redirect = False
        status_code = 200

        def raise_for_status(self):
            pass

        async def aiter_bytes(self):
            # Stream 1.5 MB in 256 KB chunks
            chunk = b"A" * (256 * 1024)
            for _ in range(6):
                yield chunk

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        def stream(self, method, url, **kwargs):
            return MockStreamResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    with pytest.raises(SSRFSecurityError) as exc_info:
        await adapter.call_agent({"message": "test"})
    assert "exceeded maximum allowed size of 1 MB" in str(exc_info.value)
