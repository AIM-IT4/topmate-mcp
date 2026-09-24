# MCP Tool Catalog

The professional branch covers creator profile, availability, 1:1 services, bookings, digital products, webinars/cohorts/courses, packages, priority DMs, CRM, orders, payments/refunds, payouts, coupons, analytics, webhooks and audit data.

Every mutation requires an `idempotency_key` of at least eight characters. Retrying the same action with the same key returns the original result rather than creating a duplicate.

`topmate_mcp_capabilities` returns the current provider, supported actions and granted scopes so clients can negotiate capabilities before planning a workflow.
