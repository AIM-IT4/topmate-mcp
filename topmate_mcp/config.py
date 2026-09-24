from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    provider: str = field(default_factory=lambda: _env("TOPMATE_PROVIDER", "sandbox").strip().lower())
    creator_id: str = field(default_factory=lambda: _env("TOPMATE_CREATOR_ID", "demo_creator").strip())
    profile_url: str = field(
        default_factory=lambda: _env("TOPMATE_PROFILE_URL", "https://topmate.io/amit_kumar_jha").strip()
    )

    # none: local demo, bearer: legacy single token, multi_bearer: per-tenant token map,
    # jwt: externally issued JWT/OIDC access tokens.
    auth_mode: str = field(default_factory=lambda: _env("MCP_AUTH_MODE", "none").strip().lower())
    bearer_token: str | None = field(default_factory=lambda: os.getenv("MCP_BEARER_TOKEN"))
    tenant_tokens_json: str = field(default_factory=lambda: _env("MCP_TENANT_TOKENS_JSON", "[]"))

    jwt_secret: str | None = field(default_factory=lambda: os.getenv("MCP_JWT_SECRET"))
    jwks_url: str | None = field(default_factory=lambda: os.getenv("MCP_JWKS_URL"))
    jwt_issuer: str | None = field(default_factory=lambda: os.getenv("MCP_JWT_ISSUER"))
    jwt_audience: str | None = field(default_factory=lambda: os.getenv("MCP_JWT_AUDIENCE"))
    jwt_algorithms_csv: str = field(default_factory=lambda: _env("MCP_JWT_ALGORITHMS", ""))
    jwt_creator_claim: str = field(default_factory=lambda: _env("MCP_JWT_CREATOR_CLAIM", "creator_id"))
    resource_url: str | None = field(default_factory=lambda: os.getenv("MCP_RESOURCE_URL"))

    scopes_csv: str = field(
        default_factory=lambda: _env(
            "MCP_SCOPES",
            "creator:read,creator:write,availability:read,availability:write,"
            "services:read,services:write,bookings:read,bookings:write,"
            "products:read,products:write,events:read,events:write,"
            "packages:read,packages:write,messages:read,messages:write,"
            "customers:read,customers:write,orders:read,payments:read,"
            "payments:refund,payouts:read,coupons:read,coupons:write,"
            "analytics:read,webhooks:read,webhooks:write,audit:read",
        )
    )
    rate_limit_per_minute: int = field(
        default_factory=lambda: int(_env("MCP_RATE_LIMIT_PER_MINUTE", "120"))
    )
    max_cached_tenants: int = field(
        default_factory=lambda: int(_env("MCP_MAX_CACHED_TENANTS", "1000"))
    )

    @property
    def scopes(self) -> set[str]:
        return {s.strip() for s in self.scopes_csv.split(",") if s.strip()}

    @property
    def jwt_algorithms(self) -> list[str]:
        configured = [a.strip() for a in self.jwt_algorithms_csv.split(",") if a.strip()]
        if configured:
            return configured
        return ["RS256", "ES256"] if self.jwks_url else ["HS256"]

    @property
    def tenant_token_records(self) -> list[dict[str, Any]]:
        parsed = json.loads(self.tenant_tokens_json or "[]")
        if not isinstance(parsed, list):
            raise ValueError("MCP_TENANT_TOKENS_JSON must be a JSON array")
        rows: list[dict[str, Any]] = []
        for item in parsed:
            if not isinstance(item, dict):
                raise ValueError("Each tenant token record must be a JSON object")
            rows.append(item)
        return rows
