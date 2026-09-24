# Security Model

- Do not store Topmate passwords, browser cookies or captured private API tokens.
- Production must use Topmate-issued OAuth/OIDC credentials and server-side token storage.
- Creator/tenant identity must come from the authenticated principal.
- Keep payment card data out of MCP payloads; use tokenized identifiers only.
- Refund, cancellation and outbound-message actions are high-impact writes and should require explicit user confirmation by clients where appropriate.
- Webhook secrets belong in a secret manager and must never be returned by tools.
- Audit records hash payloads rather than retaining sensitive raw payloads.
- Process-local rate limits are for the alpha only; production should enforce distributed limits at the gateway/provider layer.
- The sandbox provider contains synthetic data only.
