from __future__ import annotations

import time
from typing import Any

from topmate_mcp.providers.base import TopmateProvider
from topmate_mcp.security import AuditEntry, AuditLog, IdempotencyStore, SlidingWindowLimiter, TenantContext, payload_hash


class Gateway:
    def __init__(self, provider: TopmateProvider, context: TenantContext, rate_limit_per_minute: int = 120) -> None:
        self.provider = provider
        self.context = context
        self.audit = AuditLog()
        self.idempotency = IdempotencyStore()
        self.limiter = SlidingWindowLimiter(rate_limit_per_minute)

    async def read(self, action: str, scope: str, payload: dict[str, Any] | None = None) -> Any:
        self.context.require(scope)
        self.limiter.check(f"{self.context.creator_id}:{action}")
        return await self.provider.call(action, dict(payload or {}), self.context)

    async def write(self, action: str, scope: str, payload: dict[str, Any], idempotency_key: str) -> Any:
        if not idempotency_key or len(idempotency_key) < 8:
            raise ValueError("idempotency_key must be at least 8 characters for write operations")
        self.context.require(scope)
        self.limiter.check(f"{self.context.creator_id}:{action}")
        prior = self.idempotency.get(action, idempotency_key)
        if prior is not None:
            return {"idempotent_replay": True, "result": prior}
        digest = payload_hash(payload)
        try:
            result = await self.provider.call(action, dict(payload), self.context)
            self.idempotency.put(action, idempotency_key, result)
            self.audit.append(AuditEntry(time.time(), self.context.actor_id, self.context.creator_id, action, "success", digest))
            return {"idempotent_replay": False, "result": result}
        except Exception as exc:
            self.audit.append(AuditEntry(time.time(), self.context.actor_id, self.context.creator_id, action, "error", digest, {"error": type(exc).__name__}))
            raise
