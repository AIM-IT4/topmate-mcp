# Topmate MCP Gateway

Multi-tenant creator-commerce MCP gateway for Topmate-compatible workflows.

## Current production boundary

This repository now has a real multi-user authentication and tenant-isolation layer. The MCP request never accepts a creator ID as a tool argument; creator identity, scopes and provider mode come from the authenticated principal.

The full write surface is still demonstrated through the sandbox provider. Live Topmate mutations must use an official Topmate-authorized API/OAuth adapter. The project intentionally does not capture browser cookies, passwords or reverse-engineer private endpoints.

## Creator workflows

- creator profile and availability
- 1:1 session/service creation and updates
- booking creation, rescheduling and cancellation
- digital-product creation, update and publish
- webinars, cohorts, courses and group events
- packages/bundles
- priority DMs / creator messaging
- customer CRM and notes
- orders, payments, refunds and payouts
- coupons
- creator analytics
- webhooks
- capability discovery
- scope enforcement
- tenant-local idempotent writes
- tenant-local mutation audit trail
- tenant-local rate limiting

## Authentication modes

### 1. Local demo

```bash
MCP_AUTH_MODE=none
TOPMATE_PROVIDER=sandbox
TOPMATE_CREATOR_ID=demo_creator
```

### 2. Legacy protected preview

```bash
MCP_AUTH_MODE=bearer
MCP_BEARER_TOKEN=<one-preview-token>
```

This keeps the previous single-account protected-preview behavior.

### 3. Multi-user pilot

Use a different opaque bearer token per creator. Only SHA-256 token digests are configured on the server.

```bash
MCP_AUTH_MODE=multi_bearer
MCP_TENANT_TOKENS_JSON='[
  {
    "token_sha256": "<sha256-of-user-token>",
    "creator_id": "creator_123",
    "actor_id": "user_123",
    "provider": "sandbox",
    "scopes": ["services:read", "services:write", "bookings:read", "bookings:write"]
  }
]'
```

### 4. JWT / OIDC production login

For a real account-login flow, let an identity provider issue short-lived JWT access tokens and configure this gateway to verify them.

RS256/JWKS example:

```bash
MCP_AUTH_MODE=jwt
MCP_JWKS_URL=https://<issuer>/.well-known/jwks.json
MCP_JWT_ISSUER=https://<issuer>/
MCP_JWT_AUDIENCE=topmate-mcp
MCP_JWT_CREATOR_CLAIM=creator_id
MCP_JWT_ALGORITHMS=RS256
```

HS256 is also supported for controlled deployments through `MCP_JWT_SECRET`.

Expected claims:

```json
{
  "sub": "user_123",
  "creator_id": "creator_123",
  "scope": "services:read services:write bookings:read bookings:write",
  "provider": "sandbox",
  "exp": 1790260000
}
```

The gateway derives the tenant from this token. A client cannot switch to another creator by changing MCP tool arguments.

## Tenant isolation

Each authenticated creator gets an isolated runtime containing:

- provider instance / provider state
- idempotency store
- audit log
- sliding-window rate limiter

Two creators can reuse the same idempotency key without colliding.

The current in-process stores are appropriate for sandbox/pilot testing. At larger scale, move idempotency, audit and distributed rate limiting to durable infrastructure.

## Endpoints

- `GET /` — deployment metadata
- `GET /health` — health check
- `GET /capabilities` — gateway-level capabilities
- `GET /auth/session` — validates the supplied bearer/JWT and returns the non-secret principal
- `/mcp` — stateless Streamable HTTP MCP endpoint

## Run

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Deployment

The app remains compatible with Vercel's Python ASGI runtime. Set authentication secrets and issuer configuration as environment variables; never commit live tokens.

See `docs/ARCHITECTURE.md`, `docs/TOOL_CATALOG.md`, and `SECURITY.md`.
