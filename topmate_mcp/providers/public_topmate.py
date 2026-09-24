from __future__ import annotations

from typing import Any

import httpx
from bs4 import BeautifulSoup

from topmate_mcp.providers.base import TopmateProvider, UnsupportedAction
from topmate_mcp.security import TenantContext


class PublicTopmateProvider(TopmateProvider):
    name = "public_topmate"
    capabilities = frozenset({"creator.get", "services.list"})

    def __init__(self, profile_url: str) -> None:
        self.profile_url = profile_url

    async def _html(self) -> str:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(self.profile_url, headers={"User-Agent": "topmate-mcp/1.0"})
            response.raise_for_status()
            return response.text

    async def call(self, action: str, payload: dict[str, Any], context: TenantContext) -> Any:
        if action not in self.capabilities:
            raise UnsupportedAction(f"{action} is unavailable on the public provider")
        soup = BeautifulSoup(await self._html(), "html.parser")
        if action == "creator.get":
            h1 = soup.find("h1")
            return {
                "profile_url": self.profile_url,
                "name": h1.get_text(" ", strip=True) if h1 else None,
                "source": "public_topmate_profile",
            }
        services: list[dict[str, Any]] = []
        for heading in soup.find_all(["h2", "h3", "h4"]):
            label = heading.get_text(" ", strip=True)
            if label and len(label) < 200:
                services.append({"title": label})
        return services[:50]
