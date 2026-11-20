"""Which IP address a request really comes from.

On Render, requests pass through Cloudflare and Render's own proxy before reaching Django. Each one
appends to X-Forwarded-For without removing what the browser sent, so neither the first entry (the
browser can fake it) nor the last (a proxy) is reliable. Cloudflare sets CF-Connecting-IP to the
visitor's address, overwriting any value the browser sends, so that header is used when present.
"""
import ipaddress

from django.conf import settings
from rest_framework.throttling import BaseThrottle, ScopedRateThrottle


def _valid(value: str) -> str:
    value = (value or "").strip()
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return ""
    return value


def client_ip(request) -> tuple[str, str]:
    """The visitor's IP and where it was read from."""
    header = settings.CLIENT_IP_HEADER
    if header:
        value = _valid(request.headers.get(header, ""))
        if value:
            return value, header
    return BaseThrottle().get_ident(request), "X-Forwarded-For" if request.META.get("HTTP_X_FORWARDED_FOR") else "REMOTE_ADDR"


class ClientIPScopedThrottle(ScopedRateThrottle):
    """The per-visitor limits (contact form, visit counting) keyed on the real visitor IP."""

    def get_ident(self, request):
        return client_ip(request)[0]
