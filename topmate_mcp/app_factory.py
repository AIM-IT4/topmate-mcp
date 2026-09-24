from __future__ import annotations

from contextlib import asynccontextmanager
from hmac import compare_digest

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from topmate_mcp.config import Settings
from topmate_mcp.providers.public_topmate import PublicTopmateProvider
from topmate_mcp.providers.sandbox import SandboxProvider
from topmate_mcp.runtime import Gateway
from topmate_mcp.security import TenantContext
from topmate_mcp.tools import register_tools


def build_app() -> FastAPI:
    settings = Settings()
    provider = PublicTopmateProvider(settings.profile_url) if settings.provider == "public" else SandboxProvider()
    context = TenantContext(settings.creator_id, frozenset(settings.scopes))
    gateway = Gateway(provider, context, settings.rate_limit_per_minute)

    mcp = MCPServer("Topmate MCP Gateway", description="Creator-commerce MCP gateway for Topmate-compatible workflows.")
    register_tools(mcp, gateway)

    security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    mcp_app = mcp.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        json_response=True,
        transport_security=security,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        async with mcp.session_manager.run():
            yield

    app = FastAPI(title="Topmate MCP Gateway", version="1.0.0-alpha.1", lifespan=lifespan)

    @app.middleware("http")
    async def auth_guard(request: Request, call_next):
        if request.url.path.startswith("/mcp") and settings.auth_mode == "bearer":
            expected = settings.bearer_token or ""
            supplied = request.headers.get("authorization", "")
            token = supplied.removeprefix("Bearer ").strip() if supplied.startswith("Bearer ") else ""
            if not expected or not compare_digest(token, expected):
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)

    @app.get("/")
    async def root():
        return {
            "service": "topmate-mcp-gateway", "status": "ok", "version": "1.0.0-alpha.1",
            "provider": provider.name, "health": "/health", "capabilities": "/capabilities", "mcp": "/mcp",
        }

    @app.get("/health")
    async def health():
        return {"status": "ok", "provider": provider.name, "mcp_endpoint": "/mcp"}

    @app.get("/capabilities")
    async def capabilities():
        return {"provider": provider.name, "actions": sorted(provider.capabilities), "scope_count": len(context.scopes), "auth_mode": settings.auth_mode}

    app.mount("/mcp", mcp_app)
    app.state.gateway = gateway
    return app
