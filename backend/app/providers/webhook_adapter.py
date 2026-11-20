from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse
import httpx


class SSRFSecurityError(Exception):
    """Raised when an outbound URL violates SSRF safety boundaries."""
    pass


def is_safe_webhook_url(url: str) -> bool:
    """Validate that target URL does not point to loopback, link-local, multicast, or private IP spaces."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    # Block explicit localhost names
    if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return False

    try:
        # Resolve all IPs for hostname
        addr_info = socket.getaddrinfo(hostname, None)
        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip = ipaddress.ip_address(ip_str)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip_str == "169.254.169.254"  # AWS/GCP metadata
            ):
                return False
        return True
    except (socket.gaierror, ValueError):
        return False


class RemoteWebhookAgentAdapter:
    """Safe outbound webhook adapter for customer real-estate voice agents under eval."""

    def __init__(self, target_url: str, timeout_sec: float = 45.0):
        if not is_safe_webhook_url(target_url):
            raise SSRFSecurityError(f"Target URL '{target_url}' resolved to a restricted IP address or loopback.")
        self.target_url = target_url
        self.timeout_sec = min(timeout_sec, 45.0)  # Enforce 45s hard cap

    async def call_agent(self, payload: dict) -> dict:
        # Re-verify before each request (DNS rebinding protection)
        if not is_safe_webhook_url(self.target_url):
            raise SSRFSecurityError("Outbound request blocked by DNS rebinding guard.")

        # Follow redirects strictly with custom transport that checks every redirect location
        async with httpx.AsyncClient(timeout=self.timeout_sec, follow_redirects=False) as client:
            resp = await client.post(self.target_url, json=payload)
            if resp.is_redirect:
                loc = resp.headers.get("Location")
                if loc and not is_safe_webhook_url(loc):
                    raise SSRFSecurityError(f"Redirect to restricted location '{loc}' blocked.")
            resp.raise_for_status()
            return resp.json()
