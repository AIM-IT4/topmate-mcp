from __future__ import annotations

import time
from collections import OrderedDict
from threading import RLock
from typing import Any

from topmate_mcp.auth import TenantPrincipal, get_current_principal
from topmate_mcp.providers.base import TopmateProvider
from topmate_mcp.providers.public_topmate import PublicTopmateProvider
from topmate_mcp.providers.sandbox import SandboxProvider
from topmate_mcp.security import (
    AuditEntry,
    AuditLog,
    IdempotencyStore,
    SlidingWindowLimiter,
    TenantContext,
    payload_hash,
)


class Gateway:
    def __init__(
        self,
        provider: TopmateProvider,
        context: TenantContext,
        rate_limit_per_minute: int = 120,
        *,
        audit: AuditLog | None = None,
        idempotency: IdempotencyStore | None = None,
        limiter: SlidingWindowLimiter | None = None,
    ) -> None:
        self.provider = provider
        self.context = context
        self.audit = audit or AuditLog()
        self.idempotency = idempotency or IdempotencyStore()
        self.limiter = limiter or SlidingWindowLimiter(rate_limit_per_minute)

    async def read(
        self, action: str, scope: str, payload: dict[str, Any] | None = None
    ) -> Any:
        self.context.require(scope)
        self.limiter.check(f"{self.context.creator_id}:{action}")
        return await self.provider.call(action, dict(payload or {}), self.context)

    async def write(
        self,
        action: str,
        scope: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> Any:
        if not idempotency_key or len(idempotency_key) < 8:
            raise ValueError(
                "idempotency_key must be at least 8 characters for write operations"
            )
        self.context.require(scope)
        self.limiter.check(f"{self.context.creator_id}:{action}")
        prior = self.idempotency.get(action, idempotency_key)
        if prior is not None:
            return {"idempotent_replay": True, "result": prior}

        digest = payload_hash(payload)
        try:
            result = await self.provider.call(action, dict(payload), self.context)
            self.idempotency.put(action, idempotency_key, result)
            self.audit.append(
                AuditEntry(
                    time.time(),
                    self.context.actor_id,
                    self.context.creator_id,
                    action,
                    "success",
                    digest,
                )
            )
            return {"idempotent_replay": False, "result": result}
        except Exception as exc:
            self.audit.append(
                AuditEntry(
                    time.time(),
                    self.context.actor_id,
                    self.context.creator_id,
                    action,
                    "error",
                    digest,
                    {"error": type(exc).__name__},
                )
            )
            raise

    def describe(self) -> dict[str, Any]:
        return {
            "provider": self.provider.name,
            "actions": sorted(self.provider.capabilities),
            "scopes": sorted(self.context.scopes),
            "creator_id": self.context.creator_id,
            "actor_id": self.context.actor_id,
        }

    def audit_entries(self, limit: int = 100) -> list[dict[str, Any]]:
        self.context.require("audit:read")
        return self.audit.list(limit)


class TenantRuntime:
    def __init__(self, provider: TopmateProvider, rate_limit_per_minute: int) -> None:
        self.provider = provider
        self.audit = AuditLog()
        self.idempotency = IdempotencyStore()
        self.limiter = SlidingWindowLimiter(rate_limit_per_minute)


class TenantGatewayRouter:
    """Resolve the active tenant for each request and keep tenant state isolated."""

    def __init__(
        self,
        default_principal: TenantPrincipal,
        rate_limit_per_minute: int = 120,
        max_cached_tenants: int = 1000,
    ) -> None:
        self.default_principal = default_principal
        self.rate_limit_per_minute = rate_limit_per_minute
        self.max_cached_tenants = max(1, max_cached_tenants)
        self._runtimes: OrderedDict[str, TenantRuntime] = OrderedDict()
        self._lock = RLock()

    def _principal(self) -> TenantPrincipal:
        return get_current_principal() or self.default_principal

    @staticmethod
    def _cache_key(principal: TenantPrincipal) -> str:
        return "\x1f".join(
            [
                principal.creator_id,
                principal.provider,
                principal.profile_url or "",
            ]
        )

    @staticmethod
    def _build_provider(principal: TenantPrincipal) -> TopmateProvider:
        if principal.provider == "sandbox":
            return SandboxProvider(creator_id=principal.creator_id)
        if principal.provider == "public":
            if not principal.profile_url:
                raise ValueError("public provider requires profile_url")
            return PublicTopmateProvider(principal.profile_url)
        raise ValueError(f"Unsupported provider: {principal.provider}")

    def _runtime(self, principal: TenantPrincipal) -> TenantRuntime:
        key = self._cache_key(principal)
        with self._lock:
            existing = self._runtimes.get(key)
            if existing is not None:
                self._runtimes.move_to_end(key)
                return existing

            runtime = TenantRuntime(
                self._build_provider(principal),
                self.rate_limit_per_minute,
            )
            self._runtimes[key] = runtime
            self._runtimes.move_to_end(key)
            while len(self._runtimes) > self.max_cached_tenants:
                self._runtimes.popitem(last=False)
            return runtime

    def current_gateway(self) -> Gateway:
        principal = self._principal()
        runtime = self._runtime(principal)
        return Gateway(
            provider=runtime.provider,
            context=principal.tenant_context(),
            rate_limit_per_minute=self.rate_limit_per_minute,
            audit=runtime.audit,
            idempotency=runtime.idempotency,
            limiter=runtime.limiter,
        )

    async def read(
        self, action: str, scope: str, payload: dict[str, Any] | None = None
    ) -> Any:
        return await self.current_gateway().read(action, scope, payload)

    async def write(
        self,
        action: str,
        scope: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> Any:
        return await self.current_gateway().write(
            action, scope, payload, idempotency_key
        )

    def describe(self) -> dict[str, Any]:
        return self.current_gateway().describe()

    def audit_entries(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.current_gateway().audit_entries(limit)

    @property
    def cached_tenant_count(self) -> int:
        with self._lock:
            return len(self._runtimes)
