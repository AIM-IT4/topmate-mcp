# Topmate MCP Gateway — Architecture

## Product goal

Expose the creator-commerce surface of Topmate to AI clients through stable MCP tools while keeping provider-specific API details behind an adapter boundary.

```text
ChatGPT / Claude / Codex / Cursor
              |
        Streamable HTTP MCP
              |
     Topmate MCP Gateway
      |      |       |
   scopes  audit  idempotency
      |      |       |
        Provider contract
        /             \
SandboxProvider   TopmateProvider
(full demo)       (official API adapter)
```

## Design principles

1. **No private endpoint guessing.** The production Topmate adapter is added only against an authorized API contract.
2. **Stable MCP contracts.** AI clients should not change when Topmate changes internal services.
3. **Least privilege.** Every tool maps to an explicit scope.
4. **Safe retries.** Every mutation requires an idempotency key.
5. **Auditable writes.** Mutation attempts are recorded with actor, tenant, action, outcome and a payload hash; raw secrets are not logged.
6. **Multi-tenant boundary.** Creator identity is supplied by authenticated context, not trusted from tool arguments.
7. **Serverless-friendly transport.** Stateless Streamable HTTP is used for the MCP transport.

## Provider modes

### sandbox
Implements the complete workflow surface with synthetic creator/customer state. Intended for demos, contract tests and Topmate stakeholder evaluation.

### public
Reads a public Topmate profile. It intentionally rejects creator-side write actions.

### future topmate_api
Production adapter for Topmate-authorized APIs. It translates provider responses into stable MCP contracts and maps Topmate OAuth scopes to gateway scopes.

## Authentication

The alpha gateway supports MCP_AUTH_MODE=none for isolated demos and MCP_AUTH_MODE=bearer for protected previews. A production Topmate deployment should use OAuth 2.1 / OIDC with PKCE, consent, revocation and short-lived access tokens.

## Persistence

The sandbox provider is intentionally ephemeral. Production state remains owned by Topmate. A persistent standalone demo can add Postgres/Supabase without changing the MCP tool contracts.
