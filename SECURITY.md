# Security Model

- Creator/tenant identity is derived from the authenticated principal, never trusted from MCP tool arguments.
- Production account login should use short-lived JWT/OIDC access tokens with issuer and audience validation.
- Opaque multi-user pilot tokens are stored as SHA-256 digests, not plaintext values.
- Do not store Topmate passwords, browser cookies or captured private API tokens.
- Live Topmate writes require Topmate-issued authorization and an official provider adapter.
- Keep payment card data out of MCP payloads; use tokenized payment identifiers only.
- Refund, cancellation and outbound-message actions are high-impact writes and should require explicit user confirmation by clients where appropriate.
- Webhook secrets belong in a secret manager and must never be returned by tools.
- Audit records hash mutation payloads rather than retaining sensitive raw payloads.
- Idempotency, audit data and rate limiting are isolated by creator in the current process.
- For horizontally scaled production, move rate limits, idempotency and audit state to durable shared infrastructure.
- JWT signing secrets, JWKS configuration and tenant-token registries belong in deployment secrets/environment configuration.
- The sandbox provider contains synthetic data only.
