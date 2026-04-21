"""
Microsoft Learn Search MCP Server.

Self-hostable MCP server that exposes the Microsoft Learn documentation
search + article content to any MCP-compatible client (Claude, Copilot,
Cursor, Agent Framework, etc.).

Tools:
  search(query, locale?, top?, scope?)   — top-N Learn results for a query
  get_article(url, max_chars?)            — Markdown of a Learn article
  list_known_scopes()                     — helper: common product scopes
                                            (azure, dotnet, powershell…)

No authentication required — uses the public learn.microsoft.com/api/search.

Exposed on Streamable HTTP at /mcp (default port 8000).
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

SEARCH_ENDPOINT = "https://learn.microsoft.com/api/search"
LEARN_PREFIX = "https://learn.microsoft.com/"

# Popular scope keywords — MS Learn uses these in the `scope` filter
KNOWN_SCOPES = [
    "Azure",
    "Azure OpenAI",
    "Azure AI Foundry",
    "Microsoft Fabric",
    ".NET",
    "PowerShell",
    "Microsoft 365",
    "Power Platform",
    "Copilot Studio",
    "Microsoft Graph",
    "Windows",
    "Visual Studio",
    "GitHub",
    "Microsoft Entra",
]

_default_hosts = [
    "microsoft-learn-search-mcp",
    "microsoft-learn-search-mcp:8000",
    "localhost", "localhost:8000",
    "127.0.0.1", "127.0.0.1:8000",
]
_extra_hosts = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]

mcp = FastMCP(
    name="microsoft-learn-search-mcp",
    instructions=(
        "Search Microsoft Learn documentation and retrieve article content. "
        "Prefer `search` first to find relevant URLs, then `get_article` to pull the "
        "full article as Markdown. Results cover Azure, Microsoft 365, Fabric, Power "
        "Platform, .NET, PowerShell, Graph, Windows, Visual Studio, GitHub and more."
    ),
    transport_security=TransportSecuritySettings(
        allowed_hosts=_default_hosts + _extra_hosts,
    ),
)

_http = httpx.Client(
    timeout=20.0,
    follow_redirects=True,
    headers={"User-Agent": "microsoft-learn-search-mcp/0.1 (+https://github.com/ppiova/mcp-servers-microsoft-ecosystem)"},
)


@mcp.tool()
def search(
    query: str,
    locale: str = "en-us",
    top: int = 10,
    scope: str | None = None,
) -> dict[str, Any]:
    """Search Microsoft Learn documentation.

    Args:
        query: What to search for. Plain natural-language works.
        locale: Language/region code — e.g. "en-us", "es-es", "pt-br".
        top: Max results to return (1-50).
        scope: Optional product scope filter — e.g. "Azure", ".NET",
               "Microsoft Fabric", "Microsoft 365". Call
               `list_known_scopes` to see common values.

    Returns:
        dict with `count` and `results[]` (each has `title`, `url`, `description`).
    """
    top = max(1, min(top, 50))
    params: dict[str, Any] = {
        "search": query,
        "locale": locale,
        "$top": top,
    }
    if scope:
        params["scope"] = scope

    r = _http.get(SEARCH_ENDPOINT, params=params)
    r.raise_for_status()
    data = r.json()

    results = []
    for hit in data.get("results", []):
        results.append({
            "title": hit.get("title"),
            "url": hit.get("url"),
            "description": (hit.get("description") or "").strip(),
        })
    return {"count": len(results), "results": results}


@mcp.tool()
def get_article(url: str, max_chars: int = 20_000) -> dict[str, Any]:
    """Fetch a Microsoft Learn article and return its content as Markdown.

    Args:
        url: Full `https://learn.microsoft.com/...` URL. Returned by `search`.
        max_chars: Truncate to this length (default 20,000). Use when the
                   article is huge and you only need an overview.

    Returns:
        dict with `url`, `title`, `word_count`, `markdown`, `truncated`.
    """
    if not url.startswith(LEARN_PREFIX):
        raise ValueError(f"URL must be on {LEARN_PREFIX} — got {url!r}")

    r = _http.get(url)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    title = (soup.title.string.strip() if soup.title and soup.title.string else "").split("|")[0].strip()

    # Pull out just the main article content — strip nav/footer/aside/scripts
    main = soup.find("main") or soup.find("div", id="main") or soup.body
    if main is None:
        return {"url": str(r.url), "title": title, "word_count": 0, "markdown": "", "truncated": False}

    for tag in main.find_all(["nav", "footer", "script", "style", "aside", "noscript", "svg"]):
        tag.decompose()

    md = markdownify(str(main), heading_style="ATX", strip=["script", "style"])
    # Collapse runs of blank lines
    md = "\n".join(line for line in md.splitlines() if line.strip() or md.splitlines().count("") < 3)
    md = md.strip()

    truncated = False
    if len(md) > max_chars:
        md = md[:max_chars].rsplit("\n", 1)[0] + "\n\n…"
        truncated = True

    return {
        "url": str(r.url),
        "title": title,
        "word_count": len(md.split()),
        "markdown": md,
        "truncated": truncated,
    }


@mcp.tool()
def list_known_scopes() -> list[str]:
    """Return a curated list of popular `scope` filter values for `search`.

    Handy when you want to restrict results to a specific Microsoft product
    area (e.g. only Azure AI Foundry articles).
    """
    return KNOWN_SCOPES


if __name__ == "__main__":
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))
    mcp.settings.host = host
    mcp.settings.port = port
    print(
        f"[microsoft-learn-search-mcp] Streamable HTTP listening on http://{host}:{port}/mcp",
        flush=True,
    )
    mcp.run(transport="streamable-http")
