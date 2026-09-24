from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from topmate_mcp.security import TenantContext


class ProviderError(RuntimeError):
    pass


class UnsupportedAction(ProviderError):
    pass


class TopmateProvider(ABC):
    name: str
    capabilities: frozenset[str]

    @abstractmethod
    async def call(self, action: str, payload: dict[str, Any], context: TenantContext) -> Any:
        raise NotImplementedError

    def supports(self, action: str) -> bool:
        return action in self.capabilities
