"""
Azure AI Foundry Agents MCP Server.

Expose your Azure AI Foundry **agents** (the hosted agent service in
Microsoft Foundry projects) as MCP tools. Any MCP client — Claude,
Copilot, Cursor, Microsoft Agent Framework — can discover, invoke and
chat with agents you've built in Foundry, without writing any SDK code.

Typical pattern
---------------
* You design specialized domain agents in **Foundry Portal** (an HR agent,
  a knowledge-base Q&A agent, a code-review agent), each with its own
  instructions, tools and grounding.
* Your main orchestrator agent (wherever it runs) uses this MCP server as
  a single tool surface to call any of those Foundry agents on demand.

Tools
-----
  list_agents()                               — all agents in the project
  get_agent(agent_id)                         — full metadata
  create_thread()                             — new conversation thread
  add_message(thread_id, content, role?)      — post to a thread
  run_agent(thread_id, agent_id, timeout?)    — execute + wait + return messages
  list_messages(thread_id, limit?)            — thread history
  quick_ask(agent_id, prompt, timeout?)       — one-shot: thread + run + answer

Config
------
  AZURE_AI_PROJECT_ENDPOINT   — full project URL, e.g.
      https://<resource>.services.ai.azure.com/api/projects/<project-name>

Auth via DefaultAzureCredential (service principal, az login, or Managed
Identity). The identity must have the **"Azure AI User"** role on the
Foundry project.

Streamable HTTP on /mcp (default port 8000).
"""
from __future__ import annotations

import os
import time
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

PROJECT_ENDPOINT = (
    os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    or os.environ.get("PROJECT_ENDPOINT")
)

_default_hosts = [
    "azure-ai-foundry-agents-mcp",
    "azure-ai-foundry-agents-mcp:8000",
    "localhost", "localhost:8000",
    "127.0.0.1", "127.0.0.1:8000",
]
_extra_hosts = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]

mcp = FastMCP(
    name="azure-ai-foundry-agents-mcp",
    instructions=(
        "Discover and invoke Azure AI Foundry agents as MCP tools. Use `list_agents` "
        "to see what's available, then `quick_ask(agent_id, prompt)` for one-shot "
        "delegation, or the manual thread workflow (create_thread → add_message → "
        "run_agent → list_messages) for multi-turn conversations."
    ),
    transport_security=TransportSecuritySettings(
        allowed_hosts=_default_hosts + _extra_hosts,
    ),
)


def _client() -> AIProjectClient:
    if not PROJECT_ENDPOINT:
        raise RuntimeError(
            "AZURE_AI_PROJECT_ENDPOINT is not set. Provide the full Foundry "
            "project endpoint, e.g. "
            "https://<resource>.services.ai.azure.com/api/projects/<project-name>"
        )
    return AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )


def _message_to_dict(m: Any) -> dict[str, Any]:
    content_items: list[str] = []
    for c in getattr(m, "content", None) or []:
        text = getattr(c, "text", None)
        value = getattr(text, "value", None) if text else None
        if value:
            content_items.append(value)
    created = getattr(m, "created_at", None)
    return {
        "id": getattr(m, "id", None),
        "role": getattr(m, "role", None),
        "content": content_items,
        "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
    }


@mcp.tool()
def list_agents() -> list[dict[str, Any]]:
    """List every agent defined in the configured Foundry project."""
    project = _client()
    out: list[dict[str, Any]] = []
    for a in project.agents.list_agents():
        out.append({
            "id": a.id,
            "name": a.name,
            "model": a.model,
            "description": getattr(a, "description", None) or "",
        })
    return out


@mcp.tool()
def get_agent(agent_id: str) -> dict[str, Any]:
    """Full metadata for an agent — instructions, tools, model, etc."""
    project = _client()
    a = project.agents.get_agent(agent_id)
    return {
        "id": a.id,
        "name": a.name,
        "model": a.model,
        "description": getattr(a, "description", None),
        "instructions": getattr(a, "instructions", None),
        "tools": [{"type": getattr(t, "type", None)} for t in (getattr(a, "tools", None) or [])],
        "metadata": getattr(a, "metadata", None),
    }


@mcp.tool()
def create_thread() -> dict[str, Any]:
    """Create a new conversation thread. Returns `{thread_id}`."""
    project = _client()
    t = project.agents.threads.create()
    return {"thread_id": t.id}


@mcp.tool()
def add_message(thread_id: str, content: str, role: str = "user") -> dict[str, Any]:
    """Post a message to a thread. Role is typically "user"."""
    project = _client()
    m = project.agents.messages.create(thread_id=thread_id, role=role, content=content)
    return _message_to_dict(m)


@mcp.tool()
def run_agent(thread_id: str, agent_id: str, timeout_seconds: int = 120) -> dict[str, Any]:
    """Execute an agent on a thread and wait for it to finish (or timeout).

    Returns the final run state plus the 5 most recent messages on the thread.
    """
    project = _client()
    run = project.agents.runs.create(thread_id=thread_id, agent_id=agent_id)
    deadline = time.time() + timeout_seconds
    terminal = {"completed", "failed", "cancelled", "expired", "requires_action"}
    while run.status not in terminal and time.time() < deadline:
        time.sleep(1)
        run = project.agents.runs.get(thread_id=thread_id, run_id=run.id)

    msgs = [_message_to_dict(m) for m in project.agents.messages.list(
        thread_id=thread_id, order="desc", limit=5,
    )]
    usage = getattr(run, "usage", None)
    return {
        "run_id": run.id,
        "status": run.status,
        "last_error": getattr(run, "last_error", None).__dict__ if getattr(run, "last_error", None) else None,
        "usage": {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        } if usage else None,
        "messages": msgs,
    }


@mcp.tool()
def list_messages(thread_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Return the last N messages on a thread (most recent first)."""
    project = _client()
    return [
        _message_to_dict(m) for m in project.agents.messages.list(
            thread_id=thread_id, order="desc", limit=limit,
        )
    ]


@mcp.tool()
def quick_ask(agent_id: str, prompt: str, timeout_seconds: int = 120) -> dict[str, Any]:
    """One-shot delegation: creates a thread, posts the prompt, runs the agent,
    and returns just the assistant's final reply text.

    Use this for stateless "ask an agent" calls. Use the thread workflow
    (`create_thread` / `add_message` / `run_agent`) for multi-turn conversations.
    """
    project = _client()
    thread = project.agents.threads.create()
    project.agents.messages.create(thread_id=thread.id, role="user", content=prompt)

    run = project.agents.runs.create(thread_id=thread.id, agent_id=agent_id)
    deadline = time.time() + timeout_seconds
    terminal = {"completed", "failed", "cancelled", "expired", "requires_action"}
    while run.status not in terminal and time.time() < deadline:
        time.sleep(1)
        run = project.agents.runs.get(thread_id=thread.id, run_id=run.id)

    # Get the last assistant message
    last_msgs = list(project.agents.messages.list(
        thread_id=thread.id, order="desc", limit=10,
    ))
    assistant = next((m for m in last_msgs if getattr(m, "role", None) == "assistant"), None)
    answer_parts: list[str] = []
    for c in getattr(assistant, "content", None) or []:
        text = getattr(c, "text", None)
        value = getattr(text, "value", None) if text else None
        if value:
            answer_parts.append(value)

    return {
        "thread_id": thread.id,
        "run_id": run.id,
        "status": run.status,
        "answer": "\n\n".join(answer_parts),
    }


if __name__ == "__main__":
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))
    mcp.settings.host = host
    mcp.settings.port = port
    status = PROJECT_ENDPOINT or "MISSING — set AZURE_AI_PROJECT_ENDPOINT"
    print(
        f"[azure-ai-foundry-agents-mcp] Streamable HTTP listening on http://{host}:{port}/mcp",
        flush=True,
    )
    print(f"  Project endpoint: {status}", flush=True)
    mcp.run(transport="streamable-http")
