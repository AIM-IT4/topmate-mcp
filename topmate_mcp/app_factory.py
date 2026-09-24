from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from topmate_mcp.auth import (
    AuthenticationError,
    Authenticator,
    reset_current_principal,
    set_current_principal,
)
from topmate_mcp.config import Settings
from topmate_mcp.runtime import TenantGatewayRouter
from topmate_mcp.tools import register_tools


def build_app() -> FastAPI:
    settings = Settings()
    authenticator = Authenticator(settings)
    gateway = TenantGatewayRouter(
        default_principal=authenticator.default_principal(),
        rate_limit_per_minute=settings.rate_limit_per_minute,
        max_cached_tenants=settings.max_cached_tenants,
    )

    mcp = MCPServer(
        "Topmate MCP Gateway",
        description="Multi-tenant creator-commerce MCP gateway for Topmate-compatible workflows.",
    )
    register_tools(mcp, gateway)

    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
    mcp_app = mcp.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        json_response=True,
        transport_security=transport_security,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        async with mcp.session_manager.run():
            yield

    app = FastAPI(
        title="Topmate MCP Gateway",
        version="1.1.0-alpha.1",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def tenant_auth_guard(request: Request, call_next):
        if not request.url.path.startswith("/mcp"):
            return await call_next(request)

        try:
            principal = authenticator.authenticate(
                request.headers.get("authorization")
            )
        except AuthenticationError as exc:
            resource_metadata_url = (
                str(request.base_url).rstrip("/")
                + "/.well-known/oauth-protected-resource"
            )
            return JSONResponse(
                {
                    "error": "invalid_token",
                    "error_description": str(exc),
                },
                status_code=401,
                headers={
                    "WWW-Authenticate": (
                        f'Bearer resource_metadata="{resource_metadata_url}"'
                    )
                },
            )

        context_token = set_current_principal(principal)
        try:
            return await call_next(request)
        finally:
            reset_current_principal(context_token)

    @app.get("/")
    async def root():
        return {
            "service": "topmate-mcp-gateway",
            "status": "ok",
            "version": "1.1.0-alpha.1",
            "auth_mode": settings.auth_mode,
            "health": "/health",
            "session": "/auth/session",
            "capabilities": "/capabilities",
            "mcp": "/mcp",
        }

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "topmate-mcp-gateway",
            "auth_mode": settings.auth_mode,
            "mcp_endpoint": "/mcp",
        }

    @app.get("/capabilities")
    async def capabilities():
        return {
            "auth_mode": settings.auth_mode,
            "providers": ["sandbox", "public"],
            "multi_tenant": True,
            "tenant_identity_source": "authenticated principal",
            "oauth_discovery": "/.well-known/oauth-protected-resource",
        }

    @app.get("/.well-known/oauth-protected-resource")
    async def protected_resource_metadata(request: Request):
        resource = settings.resource_url or (
            str(request.base_url).rstrip("/") + "/mcp"
        )
        metadata = {
            "resource": resource,
            "scopes_supported": sorted(settings.scopes),
            "bearer_methods_supported": ["header"],
        }
        if settings.jwt_issuer:
            metadata["authorization_servers"] = [settings.jwt_issuer]
        return JSONResponse(
            metadata,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    @app.get("/auth/session")
    async def auth_session(request: Request):
        try:
            principal = authenticator.authenticate(
                request.headers.get("authorization")
            )
        except AuthenticationError as exc:
            return JSONResponse(
                {"error": "unauthorized", "detail": str(exc)},
                status_code=401,
            )
        return principal.public_dict()

    app.mount("/mcp", mcp_app)
    app.state.gateway = gateway
    app.state.authenticator = authenticator
    return app
