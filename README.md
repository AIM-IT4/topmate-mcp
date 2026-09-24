# Topmate MCP Gateway

Professional `v1-alpha` creator-commerce MCP gateway for Topmate-compatible workflows.

## What this branch contains

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
- idempotent writes
- mutation audit trail
- rate limiting
- provider abstraction for Topmate's official API

## Provider modes

`TOPMATE_PROVIDER=sandbox` gives a complete synthetic demo. `TOPMATE_PROVIDER=public` exposes only public Topmate reads. The future production adapter plugs Topmate-authorized APIs into the same action contract; this project does not reverse-engineer private Topmate endpoints.

## Environment

```bash
TOPMATE_PROVIDER=sandbox
TOPMATE_CREATOR_ID=demo_creator
TOPMATE_PROFILE_URL=https://topmate.io/amit_kumar_jha
MCP_AUTH_MODE=none
MCP_BEARER_TOKEN=
MCP_RATE_LIMIT_PER_MINUTE=120
```

## Run

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

Endpoints: `/health`, `/capabilities`, and MCP at `/mcp`.

See `docs/ARCHITECTURE.md`, `docs/TOOL_CATALOG.md`, and `SECURITY.md`.
