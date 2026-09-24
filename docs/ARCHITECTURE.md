# Topmate MCP Gateway — Architecture

## Product goal

Expose creator-commerce workflows through stable MCP tools while isolating each creator account and keeping provider-specific details behind an adapter boundary.

```text
ChatGPT / Claude / Codex / Cursor
              |
        Bearer / OIDC JWT
              |
      FastAPI auth middleware
              |
     authenticated principal
      creator + actor + scopes
              |
       ContextVar boundary
              |
      TenantGatewayRouter
       /        |        \
 provider   idempotency   audit/rate-limit
    |
 Provider contract
  /          \
sandbox    public
              \
        future Topmate API
```

## Multi-tenant request model

1. The HTTP middleware authenticates every `/mcp` request.
2. Authentication yields a `TenantPrincipal`: creator ID, actor ID, scopes, provider and optional public profile URL.
3. The principal is stored in a request-local `ContextVar`.
4. MCP tools call a `TenantGatewayRouter` rather than a fixed global creator gateway.
5. The router resolves the tenant runtime and constructs a request-scoped `Gateway` with the current principal.
6. Scope checks occur immediately before every provider call.
7. Idempotency, audit records and rate-limit buckets are isolated per creator runtime.

Creator identity never comes from MCP tool arguments.

## Authentication modes

- `none`: local/sandbox compatibility mode.
- `bearer`: legacy single-token protected preview.
- `multi_bearer`: hashed per-creator opaque tokens for pilots.
- `jwt`: JWT/OIDC access-token verification with either JWKS asymmetric signing or a controlled shared secret.

JWT mode can enforce issuer, audience, accepted algorithms, expiry and subject. Creator identity is read from the configured claim (default `creator_id`) with `sub` as fallback.

## Provider modes

### sandbox

Implements the workflow contract with synthetic creator/customer state. A separate sandbox provider is created for each creator, so data cannot bleed between authenticated tenants in the same process.

### public

Reads a configured public Topmate profile and intentionally rejects creator-side write actions.

### future topmate_api

Production adapter for Topmate-authorized APIs. It should exchange or forward Topmate-issued credentials server-side and translate provider responses into the stable MCP contract.

No private Topmate endpoint guessing is part of this project.

## State and scale

The request authentication boundary is multi-user. The sandbox provider, audit log, idempotency store and rate limiter are still process-local.

For horizontal/serverless production:

- provider-owned Topmate state should remain in Topmate;
- idempotency should move to durable Redis/Postgres;
- audit records should move to append-only durable storage;
- rate limits should move to Redis/API-gateway enforcement;
- account/provider credentials should live in a secret manager or encrypted credential store.

The `TenantGatewayRouter` has an LRU tenant-runtime cap so an unbounded number of authenticated creator IDs cannot grow process memory indefinitely.

## Security invariants

- no creator ID override in tool parameters;
- no raw opaque tenant token in configuration, only its SHA-256 digest;
- JWT signature/expiry verification before tenant selection;
- explicit scope requirement per tool;
- payload hashes in audit records instead of raw mutation bodies;
- per-tenant idempotency namespace;
- high-impact operations remain explicit MCP calls.
