from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    provider: str = os.getenv("TOPMATE_PROVIDER", "sandbox").strip().lower()
    creator_id: str = os.getenv("TOPMATE_CREATOR_ID", "demo_creator")
    profile_url: str = os.getenv("TOPMATE_PROFILE_URL", "https://topmate.io/amit_kumar_jha")
    auth_mode: str = os.getenv("MCP_AUTH_MODE", "none").strip().lower()
    bearer_token: str | None = os.getenv("MCP_BEARER_TOKEN")
    scopes_csv: str = os.getenv(
        "MCP_SCOPES",
        "creator:read,creator:write,availability:read,availability:write,services:read,services:write,bookings:read,bookings:write,products:read,products:write,events:read,events:write,packages:read,packages:write,messages:read,messages:write,customers:read,customers:write,orders:read,payments:read,payments:refund,payouts:read,coupons:read,coupons:write,analytics:read,webhooks:read,webhooks:write,audit:read",
    )
    rate_limit_per_minute: int = int(os.getenv("MCP_RATE_LIMIT_PER_MINUTE", "120"))

    @property
    def scopes(self) -> set[str]:
        return {s.strip() for s in self.scopes_csv.split(",") if s.strip()}
