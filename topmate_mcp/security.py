from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any


class PermissionDenied(RuntimeError):
    pass


class RateLimitExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class TenantContext:
    creator_id: str
    scopes: frozenset[str]
    actor_id: str = "mcp-user"

    def require(self, scope: str) -> None:
        if scope not in self.scopes:
            raise PermissionDenied(f"Missing required scope: {scope}")


@dataclass
class AuditEntry:
    ts: float
    actor_id: str
    creator_id: str
    action: str
    outcome: str
    payload_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)


class AuditLog:
    def __init__(self, max_entries: int = 1000) -> None:
        self._entries: deque[AuditEntry] = deque(maxlen=max_entries)

    def append(self, entry: AuditEntry) -> None:
        self._entries.append(entry)

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = list(self._entries)[-max(1, min(limit, 500)):]
        return [entry.__dict__.copy() for entry in reversed(rows)]


class IdempotencyStore:
    def __init__(self) -> None:
        self._results: dict[tuple[str, str], Any] = {}

    def get(self, action: str, key: str) -> Any | None:
        return self._results.get((action, key))

    def put(self, action: str, key: str, result: Any) -> None:
        self._results[(action, key)] = result


class SlidingWindowLimiter:
    def __init__(self, per_minute: int) -> None:
        self.per_minute = max(1, per_minute)
        self._hits: defaultdict[str, deque[float]] = defaultdict(deque)

    def check(self, subject: str) -> None:
        now = time.time()
        window = self._hits[subject]
        cutoff = now - 60.0
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= self.per_minute:
            raise RateLimitExceeded("Rate limit exceeded. Retry shortly.")
        window.append(now)


def payload_hash(payload: dict[str, Any]) -> str:
    normalized = repr(sorted(payload.items())).encode("utf-8", errors="replace")
    return hashlib.sha256(normalized).hexdigest()[:20]
