import asyncio
import hashlib
import json
import time

import jwt

from topmate_mcp.auth import AuthenticationError, Authenticator, TenantPrincipal, principal_scope
from topmate_mcp.config import Settings
from topmate_mcp.runtime import TenantGatewayRouter


ALL = frozenset({"services:read", "services:write", "audit:read"})


def test_multi_bearer_resolves_distinct_tenants(monkeypatch):
    alpha_token = "alpha-secret-token"
    beta_token = "beta-secret-token"
    records = [
        {
            "token_sha256": hashlib.sha256(alpha_token.encode()).hexdigest(),
            "creator_id": "creator_alpha",
            "actor_id": "user_alpha",
            "provider": "sandbox",
            "scopes": ["services:read", "services:write"],
        },
        {
            "token_sha256": hashlib.sha256(beta_token.encode()).hexdigest(),
            "creator_id": "creator_beta",
            "actor_id": "user_beta",
            "provider": "sandbox",
            "scopes": ["services:read"],
        },
    ]
    monkeypatch.setenv("MCP_AUTH_MODE", "multi_bearer")
    monkeypatch.setenv("MCP_TENANT_TOKENS_JSON", json.dumps(records))
    auth = Authenticator(Settings())

    alpha = auth.authenticate(f"Bearer {alpha_token}")
    beta = auth.authenticate(f"Bearer {beta_token}")

    assert alpha.creator_id == "creator_alpha"
    assert beta.creator_id == "creator_beta"
    assert "services:write" in alpha.scopes
    assert "services:write" not in beta.scopes


def test_tenant_sandbox_state_is_isolated():
    default = TenantPrincipal("default", ALL, "default-user", "sandbox")
    router = TenantGatewayRouter(default, rate_limit_per_minute=1000)

    alpha = TenantPrincipal("creator_alpha", ALL, "user_alpha", "sandbox")
    beta = TenantPrincipal("creator_beta", ALL, "user_beta", "sandbox")

    async def run():
        with principal_scope(alpha):
            created = await router.write(
                "services.create",
                "services:write",
                {"title": "Alpha Only", "duration_minutes": 30, "price": 1499},
                "alpha-idempotency-001",
            )
            alpha_id = created["result"]["id"]
            alpha_services = await router.read("services.list", "services:read")
            assert any(row["id"] == alpha_id for row in alpha_services)
            assert router.describe()["creator_id"] == "creator_alpha"

        with principal_scope(beta):
            beta_services = await router.read("services.list", "services:read")
            assert all(row["id"] != alpha_id for row in beta_services)
            assert router.describe()["creator_id"] == "creator_beta"

        with principal_scope(alpha):
            alpha_services_again = await router.read("services.list", "services:read")
            assert any(row["id"] == alpha_id for row in alpha_services_again)
            assert len(router.audit_entries()) == 1

    asyncio.run(run())


def test_idempotency_keys_are_tenant_local():
    default = TenantPrincipal("default", ALL, "default-user", "sandbox")
    router = TenantGatewayRouter(default, rate_limit_per_minute=1000)
    alpha = TenantPrincipal("creator_alpha", ALL, "user_alpha", "sandbox")
    beta = TenantPrincipal("creator_beta", ALL, "user_beta", "sandbox")

    async def run():
        with principal_scope(alpha):
            first = await router.write(
                "services.create",
                "services:write",
                {"title": "Alpha", "duration_minutes": 30, "price": 100},
                "shared-idempotency-key",
            )
        with principal_scope(beta):
            second = await router.write(
                "services.create",
                "services:write",
                {"title": "Beta", "duration_minutes": 45, "price": 200},
                "shared-idempotency-key",
            )

        assert first["idempotent_replay"] is False
        assert second["idempotent_replay"] is False

    asyncio.run(run())


def test_jwt_auth_maps_verified_claims_to_tenant(monkeypatch):
    secret = "test-signing-secret"
    issuer = "https://identity.example.test"
    audience = "topmate-mcp"

    monkeypatch.setenv("MCP_AUTH_MODE", "jwt")
    monkeypatch.setenv("MCP_JWT_SECRET", secret)
    monkeypatch.setenv("MCP_JWT_ISSUER", issuer)
    monkeypatch.setenv("MCP_JWT_AUDIENCE", audience)
    monkeypatch.setenv("MCP_JWT_ALGORITHMS", "HS256")

    token = jwt.encode(
        {
            "sub": "user_789",
            "creator_id": "creator_789",
            "scope": "services:read services:write",
            "provider": "sandbox",
            "iss": issuer,
            "aud": audience,
            "exp": int(time.time()) + 300,
        },
        secret,
        algorithm="HS256",
    )

    principal = Authenticator(Settings()).authenticate(f"Bearer {token}")

    assert principal.actor_id == "user_789"
    assert principal.creator_id == "creator_789"
    assert principal.scopes == frozenset({"services:read", "services:write"})


def test_jwt_auth_rejects_wrong_audience(monkeypatch):
    secret = "test-signing-secret"
    issuer = "https://identity.example.test"

    monkeypatch.setenv("MCP_AUTH_MODE", "jwt")
    monkeypatch.setenv("MCP_JWT_SECRET", secret)
    monkeypatch.setenv("MCP_JWT_ISSUER", issuer)
    monkeypatch.setenv("MCP_JWT_AUDIENCE", "topmate-mcp")
    monkeypatch.setenv("MCP_JWT_ALGORITHMS", "HS256")

    token = jwt.encode(
        {
            "sub": "user_789",
            "creator_id": "creator_789",
            "scope": "services:read",
            "iss": issuer,
            "aud": "another-service",
            "exp": int(time.time()) + 300,
        },
        secret,
        algorithm="HS256",
    )

    try:
        Authenticator(Settings()).authenticate(f"Bearer {token}")
    except AuthenticationError:
        return
    raise AssertionError("Expected AuthenticationError for wrong JWT audience")
