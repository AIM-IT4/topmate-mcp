from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from mcp.server.mcpserver import MCPServer
from starlette.responses import JSONResponse
from starlette.routing import Route

PROFILE_URL = "https://topmate.io/amit_kumar_jha"
USER_AGENT = "topmate-mcp/0.1 (+https://modelcontextprotocol.io)"
TIMEOUT = 20.0

mcp = MCPServer(
    "Topmate MCP",
    description="Read-only MCP server for Amit Kumar Jha's public Topmate profile and services.",
)


class TopmateError(RuntimeError):
    pass


def normalize_profile_url(profile_url: str) -> str:
    url = profile_url.strip()
    if not url:
        raise TopmateError("Topmate profile URL is empty.")
    if not url.startswith(("http://", "https://")):
        url = f"https://topmate.io/{url.lstrip('@/')}"
    parsed = urlparse(url)
    if parsed.hostname not in {"topmate.io", "www.topmate.io"}:
        raise TopmateError("Only topmate.io profile URLs are allowed.")
    path = parsed.path.rstrip("/")
    if not path:
        raise TopmateError("Provide a Topmate profile URL.")
    return f"https://topmate.io{path}"


async def fetch_html(profile_url: str) -> str:
    url = normalize_profile_url(profile_url)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
    }
    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        follow_redirects=True,
        headers=headers,
    ) as client:
        response = await client.get(url)
    if response.status_code >= 400:
        raise TopmateError(f"Topmate returned HTTP {response.status_code} for {url}")
    return response.text


def _match_float(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text, re.I)
    return float(match.group(1)) if match else None


def _match_compact_number(text: str, pattern: str) -> int | None:
    match = re.search(pattern, text, re.I)
    if not match:
        return None
    raw = match.group(1).lower()
    multiplier = 1
    if raw.endswith("k"):
        multiplier, raw = 1000, raw[:-1]
    elif raw.endswith("m"):
        multiplier, raw = 1_000_000, raw[:-1]
    try:
        return int(float(raw) * multiplier)
    except ValueError:
        return None


def _extract_services(
    soup: BeautifulSoup,
    full_text: str,
    json_ld: list[Any],
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None]] = set()

    def visit(obj: Any) -> None:
        if isinstance(obj, dict):
            typ = obj.get("@type")
            types = set(typ if isinstance(typ, list) else [typ])
            if {"Product", "Service", "Offer"} & types:
                name = obj.get("name")
                offer = obj.get("offers") if isinstance(obj.get("offers"), dict) else obj
                price = offer.get("price") if isinstance(offer, dict) else None
                currency = offer.get("priceCurrency") if isinstance(offer, dict) else None
                if name:
                    key = (str(name).strip(), str(price) if price is not None else None)
                    if key not in seen:
                        seen.add(key)
                        found.append(
                            {
                                "name": str(name).strip(),
                                "price": price,
                                "currency": currency,
                            }
                        )
            for value in obj.values():
                visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)

    visit(json_ld)
    if found:
        return found[:100]

    price_re = re.compile(
        r"^(?:₹|Rs\.?|INR|\$|USD|€|EUR|£|GBP)\s*[0-9][0-9,]*(?:\.\d+)?$",
        re.I,
    )
    for node in soup.find_all(string=price_re):
        price_text = re.sub(r"\s+", " ", str(node)).strip()
        container = node.parent
        for _ in range(4):
            if container is None:
                break
            candidates = container.find_all(
                ["h2", "h3", "h4", "strong", "b"],
                limit=5,
            )
            names = [
                candidate.get_text(" ", strip=True)
                for candidate in candidates
                if candidate.get_text(" ", strip=True)
            ]
            name = next((value for value in names if not price_re.match(value)), None)
            if name:
                key = (name, price_text)
                if key not in seen:
                    seen.add(key)
                    found.append({"name": name, "price_text": price_text})
                break
            container = container.parent

    if not found and "Services" in full_text:
        section = full_text.split("Services", 1)[1]
        section = re.split(
            r"\nAbout me\b|\nTestimonials\b|\nTerms\b",
            section,
            maxsplit=1,
            flags=re.I,
        )[0]
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        price_line_re = re.compile(
            r"^(FREE|(?:₹|Rs\.?|INR|\$|USD|€|EUR|£|GBP)\s*[0-9])",
            re.I,
        )
        for index, line in enumerate(lines):
            if not price_line_re.search(line):
                continue
            name = None
            for cursor in range(index - 1, max(-1, index - 5), -1):
                candidate = lines[cursor]
                if candidate.lower() not in {
                    "popular",
                    "best seller",
                    "digital product",
                    "priority dm",
                }:
                    name = candidate
                    break
            if name:
                key = (name, line)
                if key not in seen:
                    seen.add(key)
                    found.append(
                        {"name": name[:300], "price_text": line[:100]}
                    )

    return found[:100]


def parse_profile_html(profile_url: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    title = None
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(" ", strip=True)
    if not title and soup.title:
        title = (
            soup.title.get_text(" ", strip=True)
            .replace(" | Topmate", "")
            .strip()
        )

    description = None
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc["content"].strip()

    json_ld: list[Any] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text(strip=True)
        if not raw:
            continue
        try:
            json_ld.append(json.loads(raw))
        except Exception:
            pass

    about = None
    match = re.search(
        r"\bAbout me\b\s*(.+?)(?:\n(?:Terms|Privacy|Services)\b|$)",
        text,
        re.I | re.S,
    )
    if match:
        about = re.sub(r"\s+", " ", match.group(1)).strip()[:2000]

    return {
        "profile_url": normalize_profile_url(profile_url),
        "name": title,
        "description": description,
        "rating": _match_float(text, r"(?<!\d)([0-5](?:\.\d+)?)\s*/\s*5"),
        "bookings": _match_compact_number(
            text,
            r"([0-9]+(?:\.[0-9]+)?[kKmM]?)\s+bookings?\b",
        ),
        "testimonials": _match_compact_number(
            text,
            r"([0-9]+(?:\.[0-9]+)?[kKmM]?)\s+testimonials?\b",
        ),
        "about": about,
        "services": _extract_services(soup, text, json_ld),
        "source": "public_topmate_profile",
    }


@mcp.tool()
async def topmate_get_profile(
    profile_url: str | None = None,
) -> dict[str, Any]:
    """Read a public Topmate profile and return metadata plus detected services."""
    url = normalize_profile_url(profile_url or PROFILE_URL)
    return parse_profile_html(url, await fetch_html(url))


@mcp.tool()
async def topmate_list_services(
    profile_url: str | None = None,
) -> list[dict[str, Any]]:
    """List services/products detected on a public Topmate profile."""
    profile = await topmate_get_profile(profile_url)
    return profile.get("services", [])


@mcp.tool()
def topmate_mcp_status() -> dict[str, Any]:
    """Return production readiness without exposing private data."""
    return {
        "status": "ready",
        "profile_url": PROFILE_URL,
        "public_profile_tools": True,
        "private_google_tools": False,
        "transport": "streamable-http",
        "deployment_target": "vercel",
    }


async def health(_request):
    return JSONResponse(
        {
            "status": "ok",
            "service": "topmate-mcp",
            "profile_url": PROFILE_URL,
            "mcp_endpoint": "/mcp",
        }
    )


app = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
    custom_starlette_routes=[Route("/health", health, methods=["GET"])],
)
