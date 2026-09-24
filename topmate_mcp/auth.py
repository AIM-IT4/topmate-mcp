from __future__ import annotations

import hashlib
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from hmac import compare_digest
from typing import Any, Iterator

import jwt
from jwt import PyJWKClient

from topmate_mcp.config import Settings
from topmate_mcp.security import TenantContext


class AuthenticationError(RuntimeError):
    pass


@dataclass(frozen=True)
class TenantPrincipal:
    creator_id: str
    scopes: frozenset[str]
    actor_id: str
    provider: str = "sandbox"
    profile_url: str | None = None

    def tenant_context(self) -> TenantContext:
        return TenantContext(
            creator_id=self.creator_id,
            scopes=self.scopes,
            actor_id=self.actor_id,
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "creator_id": self.creator_id,
            "provider": self.provider,
            "profile_url": self.profile_url,
            "scopes": sorted(self.scopes),
        }


_current_principal: ContextVar[TenantPrincipal | None] = ContextVar(
    "topmate_current_principal", default=None
)


def get_current_principal() -> TenantPrincipal | None:
    return _current_principal.get()


def set_current_principal(principal: TenantPrincipal) -> Token:
    return _current_principal.set(principal)


def reset_current_principal(token: Token) -> None:
    _current_principal.reset(token)


@contextmanager
def principal_scope(principal: TenantPrincipal) -> Iterator[None]:
    token = set_current_principal(principal)
    try:
        yield
    finally:
        reset_current_principal(token)


def token_sha256(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _parse_scopes(value: Any) -> frozenset[str]:
    if isinstance(value, str):
        normalized = value.replace(",", " ")
        return frozenset(part.strip() for part in normalized.split() if part.strip())
    if isinstance(value, (list, tuple, set)):
        return frozenset(str(part).strip() for part in value if str(part).strip())
    return frozenset()


class Authenticator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._jwk_client = PyJWKClient(settings.jwks_url) if settings.jwks_url else None

    def default_principal(self) -> TenantPrincipal:
        return TenantPrincipal(
            creator_id=self.settings.creator_id,
            scopes=frozenset(self.settings.scopes),
            actor_id="mcp-user",
            provider=self.settings.provider,
            profile_url=self.settings.profile_url,
        )

    @staticmethod
    def _extract_bearer(authorization: str | None) -> str:
        if not authorization:
            raise AuthenticationError("missing bearer token")
        scheme, separator, token = authorization.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            raise AuthenticationError("authorization must use Bearer <token>")
        return token.strip()

    @staticmethod
    def _validated_provider(value: Any) -> str:
        provider = str(value or "sandbox").strip().lower()
        if provider not in {"sandbox", "public"}:
            raise AuthenticationError(f"unsupported provider for authenticated tenant: {provider}")
        return provider

    def _principal_from_record(self, record: dict[str, Any]) -> TenantPrincipal:
        creator_id = str(record.get("creator_id") or "").strip()
        if not creator_id:
            raise AuthenticationError("tenant record is missing creator_id")
        actor_id = str(record.get("actor_id") or creator_id).strip()
        scopes = _parse_scopes(record.get("scopes"))
        provider = self._validated_provider(record.get("provider") or self.settings.provider)
        profile_url = record.get("profile_url") or self.settings.profile_url
        return TenantPrincipal(
            creator_id=creator_id,
            scopes=scopes,
            actor_id=actor_id,
            provider=provider,
            profile_url=str(profile_url).strip() if profile_url else None,
        )

    def _authenticate_multi_bearer(self, authorization: str | None) -> TenantPrincipal:
        token = self._extract_bearer(authorization)
        supplied_digest = token_sha256(token)

        try:
            records = self.settings.tenant_token_records
        except (ValueError, TypeError) as exc:
            raise AuthenticationError(f"invalid tenant token configuration: {exc}") from exc

        for record in records:
            expected = str(record.get("token_sha256") or "").strip().lower()
            if expected and compare_digest(supplied_digest, expected):
                return self._principal_from_record(record)
        raise AuthenticationError("invalid bearer token")

    def _decode_jwt(self, token: str) -> dict[str, Any]:
        options: dict[str, Any] = {
            "require": ["exp", "sub"],
            "verify_aud": bool(self.settings.jwt_audience),
            "verify_iss": bool(self.settings.jwt_issuer),
        }
        kwargs: dict[str, Any] = {
            "algorithms": self.settings.jwt_algorithms,
            "options": options,
        }
        if self.settings.jwt_audience:
            kwargs["audience"] = self.settings.jwt_audience
        if self.settings.jwt_issuer:
            kwargs["issuer"] = self.settings.jwt_issuer

        try:
            if self._jwk_client is not None:
                signing_key = self._jwk_client.get_signing_key_from_jwt(token)
                return jwt.decode(token, signing_key.key, **kwargs)
            if not self.settings.jwt_secret:
                raise AuthenticationError(
                    "jwt auth requires MCP_JWKS_URL or MCP_JWT_SECRET"
                )
            return jwt.decode(token, self.settings.jwt_secret, **kwargs)
        except AuthenticationError:
            raise
        except Exception as exc:
            raise AuthenticationError("invalid or expired JWT") from exc

    def _authenticate_jwt(self, authorization: str | None) -> TenantPrincipal:
        token = self._extract_bearer(authorization)
        claims = self._decode_jwt(token)
        creator_id = str(
            claims.get(self.settings.jwt_creator_claim) or claims.get("sub") or ""
        ).strip()
        if not creator_id:
            raise AuthenticationError("JWT does not identify a creator")

        scopes = _parse_scopes(claims.get("scopes") or claims.get("scope"))
        provider = self._validated_provider(claims.get("provider") or self.settings.provider)
        profile_url = claims.get("profile_url") or self.settings.profile_url

        return TenantPrincipal(
            creator_id=creator_id,
            scopes=scopes,
            actor_id=str(claims.get("sub") or creator_id),
            provider=provider,
            profile_url=str(profile_url).strip() if profile_url else None,
        )

    def authenticate(self, authorization: str | None) -> TenantPrincipal:
        mode = self.settings.auth_mode
        if mode == "none":
            return self.default_principal()

        if mode == "bearer":
            token = self._extract_bearer(authorization)
            expected = self.settings.bearer_token or ""
            if not expected or not compare_digest(token, expected):
                raise AuthenticationError("invalid bearer token")
            return self.default_principal()

        if mode == "multi_bearer":
            return self._authenticate_multi_bearer(authorization)

        if mode == "jwt":
            return self._authenticate_jwt(authorization)

        raise AuthenticationError(f"unsupported MCP_AUTH_MODE: {mode}")
