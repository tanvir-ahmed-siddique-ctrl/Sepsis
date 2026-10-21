"""Per-client request budgets and request-size limits.

The hospital reverse proxy is the first line of defence (connection limits, TLS,
IP allowlists). This layer protects the API itself: login guessing, a runaway
interface engine, or a scripted client cannot starve the single writer.

Budgets are fixed one-minute windows held in process memory, which matches the
single-active-writer deployment. Clients are keyed by credential, not by name:
an integration key ID, a hash of the bearer token, the demo user at its peer
address, or the peer address. Login endpoints are always keyed by peer address.
"""

from __future__ import annotations

import hashlib
import threading
import time

from starlette.requests import Request

from app.core.config import settings

WINDOW_SECONDS = 60.0
MAX_TRACKED_CLIENTS = 50_000
EXEMPT_PATHS = frozenset({"/health", "/ready"})
LOGIN_PATHS = frozenset({"/v1/auth/login", "/v1/auth/pin-login", "/v1/auth/demo-token"})


class RateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._windows: dict[tuple[str, str], tuple[float, int]] = {}

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()

    def hit(self, bucket: str, client: str, limit: int, now: float | None = None) -> float | None:
        """Count one request. Returns seconds to wait when the budget is exhausted, else ``None``."""
        now = time.monotonic() if now is None else now
        window_start = now - (now % WINDOW_SECONDS)
        key = (bucket, client)
        with self._lock:
            if len(self._windows) >= MAX_TRACKED_CLIENTS:
                self._windows = {k: v for k, v in self._windows.items() if v[0] == window_start}
            start, count = self._windows.get(key, (window_start, 0))
            if start != window_start:
                start, count = window_start, 0
            if count >= limit:
                return max(1.0, start + WINDOW_SECONDS - now)
            self._windows[key] = (start, count + 1)
            return None


LIMITER = RateLimiter()


def _peer(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def classify(request: Request) -> tuple[str, str, int] | None:
    """Return ``(bucket, client_key, per_minute_limit)`` or ``None`` when the path is exempt."""
    path = request.url.path
    if path in EXEMPT_PATHS or request.method == "OPTIONS":
        return None
    if path in LOGIN_PATHS:
        return "login", f"ip:{_peer(request)}", settings.rate_limit_login_per_minute
    integration_key = request.headers.get("x-integration-key")
    if integration_key and path.startswith("/v1/integrations/"):
        return "ingest", f"key:{integration_key.split('.', 1)[0][:64]}", settings.rate_limit_ingest_per_minute
    authorization = request.headers.get("authorization")
    if authorization:
        client = "token:" + hashlib.sha256(authorization.encode()).hexdigest()[:16]
    elif settings.demo_mode and request.headers.get("x-demo-user"):
        client = f"demo:{request.headers['x-demo-user'][:64]}@{_peer(request)}"
    else:
        client = f"ip:{_peer(request)}"
    return "api", client, settings.rate_limit_per_minute


def oversized(request: Request) -> bool:
    declared = request.headers.get("content-length")
    return bool(declared and declared.isdigit() and int(declared) > settings.max_request_bytes)
