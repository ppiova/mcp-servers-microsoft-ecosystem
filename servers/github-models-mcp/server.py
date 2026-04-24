"""
GitHub Models MCP Server.

Expose the free-tier **GitHub Models** inference API as MCP tools.

Use cases
---------
* **Model routing** — your main agent (Azure OpenAI / Claude) delegates small
  tasks to a cheaper free-tier model via MCP (summaries, classifications).
* **Fallback** — when Azure OpenAI hits a quota wall, retry on GitHub Models.
* **Side-by-side comparison** — run the same prompt on 3 models in parallel
  and pick the best answer.
* **Model discovery** — query the live catalog without hitting docs.

Tools
-----
  list_models(publisher?)        — catalog, optional publisher filter
  get_model_info(model_id)       — full model metadata
  chat(model, prompt, system?)   — single-turn chat completion
  compare_models(models, prompt) — same prompt across N models

Auth
----
The `list_models` / `get_model_info` tools hit the **public** catalog and
need no token. Inference tools (`chat`, `compare_models`) require a GitHub PAT
with the `models:read` scope in the `GITHUB_TOKEN` env var.

Streamable HTTP on /mcp (default port 8000).
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from openai import OpenAI

CATALOG_BASE = "https://models.github.ai/catalog/models"
INFERENCE_BASE = "https://models.github.ai/inference"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

_default_hosts = [
    "github-models-mcp",
    "github-models-mcp:8000",
    "localhost", "localhost:8000",
    "127.0.0.1", "127.0.0.1:8000",
]
_extra_hosts = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]

mcp = FastMCP(
    name="github-models-mcp",
    instructions=(
        "Access the free-tier GitHub Models catalog and inference from any MCP client. "
        "Use `list_models` to discover what's available, `chat` for single-turn "
        "completions, and `compare_models` for side-by-side A/B testing. Catalog "
        "browsing is unauthenticated; inference requires GITHUB_TOKEN with `models:read`."
    ),
    transport_security=TransportSecuritySettings(
        allowed_hosts=_default_hosts + _extra_hosts,
    ),
)

_http = httpx.Client(
    timeout=20.0,
    headers={"Accept": "application/json"},
)


def _inference_client() -> OpenAI:
    if not GITHUB_TOKEN:
        raise RuntimeError(
            "GITHUB_TOKEN env var is not set. Create a PAT at "
            "https://github.com/settings/personal-access-tokens with the "
            "`models:read` scope and pass it as GITHUB_TOKEN."
        )
    return OpenAI(api_key=GITHUB_TOKEN, base_url=INFERENCE_BASE)


@mcp.tool()
def list_models(publisher: str | None = None) -> list[dict[str, Any]]:
    """List all models available on GitHub Models.

    Args:
        publisher: Optional filter — e.g. "OpenAI", "Microsoft", "Meta", "Mistral AI",
                   "Cohere", "AI21 Labs", "DeepSeek". Case-insensitive partial match.

    Returns one row per model with id, name, publisher, summary, tags,
    rate_limit_tier and supported modalities.
    """
    r = _http.get(CATALOG_BASE)
    r.raise_for_status()
    data = r.json()

    results: list[dict[str, Any]] = []
    pub_lower = publisher.lower() if publisher else None
    for m in data:
        if pub_lower and pub_lower not in (m.get("publisher") or "").lower():
            continue
        results.append({
            "id": m.get("id"),
            "name": m.get("name"),
            "publisher": m.get("publisher"),
            "summary": (m.get("summary") or "").strip(),
            "rate_limit_tier": m.get("rate_limit_tier"),
            "tags": m.get("tags", []),
            "supported_input_modalities": m.get("supported_input_modalities", []),
            "supported_output_modalities": m.get("supported_output_modalities", []),
        })
    return results


@mcp.tool()
def get_model_info(model_id: str) -> dict[str, Any]:
    """Return the full catalog entry for a model (e.g. `openai/gpt-4.1`)."""
    r = _http.get(f"{CATALOG_BASE}/{model_id}")
    r.raise_for_status()
    return r.json()


@mcp.tool()
def chat(
    model: str,
    prompt: str,
    system: str | None = None,
    max_tokens: int = 512,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Run a single-turn chat completion on a GitHub Model.

    Args:
        model: Model id, e.g. `openai/gpt-4.1-mini`, `microsoft/Phi-4`, `meta/Llama-3.3-70B-Instruct`.
               Use `list_models` to discover valid ids.
        prompt: The user message.
        system: Optional system prompt.
        max_tokens: Max tokens in the response. Default 512.
        temperature: 0.0-2.0. Default 0.7.

    Requires GITHUB_TOKEN with `models:read` scope.
    """
    client = _inference_client()
    messages: list[dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=model,
        messages=messages,  # type: ignore[arg-type]
        max_tokens=max_tokens,
        temperature=temperature,
    )
    choice = resp.choices[0]
    return {
        "model": resp.model,
        "content": choice.message.content,
        "finish_reason": choice.finish_reason,
        "usage": resp.usage.model_dump() if resp.usage else None,
    }


@mcp.tool()
def compare_models(
    models: list[str],
    prompt: str,
    system: str | None = None,
    max_tokens: int = 256,
    temperature: float = 0.7,
) -> list[dict[str, Any]]:
    """Run the same prompt across multiple models and return all responses.

    Perfect for *"which model handles this best?"* workflows. Errors on a
    single model don't fail the whole call — they appear as `{"error": ...}` rows.
    """
    out: list[dict[str, Any]] = []
    for model_id in models:
        try:
            result = chat(model_id, prompt, system=system, max_tokens=max_tokens, temperature=temperature)
            out.append({"model_requested": model_id, **result})
        except Exception as e:
            out.append({"model_requested": model_id, "error": f"{type(e).__name__}: {e}"})
    return out


if __name__ == "__main__":
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))
    mcp.settings.host = host
    mcp.settings.port = port
    token_status = "set" if GITHUB_TOKEN else "MISSING (catalog tools only)"
    print(
        f"[github-models-mcp] Streamable HTTP listening on http://{host}:{port}/mcp "
        f"(GITHUB_TOKEN={token_status})",
        flush=True,
    )
    mcp.run(transport="streamable-http")
