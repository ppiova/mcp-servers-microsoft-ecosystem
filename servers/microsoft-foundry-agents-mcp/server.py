"""
Microsoft Foundry Agents MCP Server.

Expose your **Microsoft Foundry** (formerly Azure AI Foundry) hosted
agents as MCP tools, using the **2.x SDK** (`azure-ai-projects>=2.0.1`).

Microsoft Foundry 2.x dropped the legacy *threads + messages + runs*
model and migrated to the **OpenAI Responses API**:

  * **Agents** are defined by `name` + `version` (via `PromptAgentDefinition`).
  * **Conversations** replace threads (managed by the OpenAI client).
  * **Responses** replace runs; an agent is attached via
    `extra_body={"agent_reference": {"name": <agent>, "type": "agent_reference"}}`.

This MCP server wraps that surface so any MCP client (Claude, Copilot,
Cursor, Microsoft Agent Framework) can invoke your Foundry agents
without writing SDK code.

Tools
-----
  list_agents()                                    — agents in the project
  get_agent(agent_name)                            — metadata for a single agent
  create_conversation(initial_message=None)        — returns `conversation_id`
  append_message(conversation_id, content, role)   — add user/system message
  invoke_agent(agent_name, conversation_id)        — run agent, return output_text
  list_conversation(conversation_id, limit=20)     — items in a conversation
  quick_ask(agent_name, prompt)                    — one-shot: create + invoke

Config
------
  FOUNDRY_PROJECT_ENDPOINT   — full project URL, e.g.
      https://<resource>.services.ai.azure.com/api/projects/<project-name>

Auth via DefaultAzureCredential; the identity needs the **"Azure AI User"**
role on the Foundry project.

Streamable HTTP on /mcp (default port 8000).
"""
from __future__ import annotations

import os
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

PROJECT_ENDPOINT = (
    os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    or os.environ.get("AZURE_AI_PROJECT_ENDPOINT")  # legacy name — still accepted
    or os.environ.get("PROJECT_ENDPOINT")
)

_default_hosts = [
    "microsoft-foundry-agents-mcp",
    "microsoft-foundry-agents-mcp:8000",
    "localhost", "localhost:8000",
    "127.0.0.1", "127.0.0.1:8000",
]
_extra_hosts = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]

mcp = FastMCP(
    name="microsoft-foundry-agents-mcp",
    instructions=(
        "Invoke Microsoft Foundry hosted agents from any MCP client using the "
        "v2 Responses API. Use `list_agents` to discover what's deployed, then "
        "`quick_ask(agent_name, prompt)` for one-shot delegation, or the manual "
        "conversation workflow (`create_conversation` → `append_message` → "
        "`invoke_agent`) for multi-turn flows."
    ),
    transport_security=TransportSecuritySettings(
        allowed_hosts=_default_hosts + _extra_hosts,
    ),
)


def _project() -> AIProjectClient:
    if not PROJECT_ENDPOINT:
        raise RuntimeError(
            "FOUNDRY_PROJECT_ENDPOINT is not set. Provide the full Foundry "
            "project endpoint, e.g. "
            "https://<resource>.services.ai.azure.com/api/projects/<project-name>"
        )
    return AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )


def _openai(project: AIProjectClient):
    """Get an OpenAI-compatible client scoped to the Foundry project.

    The SDK 2.x bundles openai as a direct dep. Entry point names have shifted
    across 2.0.x releases, so try the common ones before giving up.
    """
    for attr in ("get_openai_client", "inference"):
        thing = getattr(project, attr, None)
        if thing is None:
            continue
        if callable(thing):
            return thing()
        nested = getattr(thing, "get_openai_client", None)
        if callable(nested):
            return nested()
    raise RuntimeError(
        "Could not obtain an OpenAI client from AIProjectClient. "
        "Ensure azure-ai-projects>=2.0.1 is installed."
    )


def _agent_to_dict(a: Any) -> dict[str, Any]:
    latest = getattr(getattr(a, "versions", None), "latest", None)
    return {
        "id": getattr(a, "id", None),
        "name": getattr(a, "name", None),
        "description": getattr(a, "description", None),
        "latest_version": getattr(latest, "version", None),
        "latest_model": getattr(getattr(latest, "definition", None), "model", None),
    }


@mcp.tool()
def list_agents() -> list[dict[str, Any]]:
    """List every agent deployed in the configured Microsoft Foundry project."""
    with _project() as project:
        try:
            iterator = project.agents.list()
        except AttributeError:
            iterator = project.agents.list_versions()
        return [_agent_to_dict(a) for a in iterator]


@mcp.tool()
def get_agent(agent_name: str) -> dict[str, Any]:
    """Return metadata for a specific agent (latest version) — instructions, model, tools."""
    with _project() as project:
        agent = project.agents.get(agent_name=agent_name)
        base = _agent_to_dict(agent)
        latest = getattr(getattr(agent, "versions", None), "latest", None)
        defn = getattr(latest, "definition", None)
        if defn is not None:
            base["instructions"] = getattr(defn, "instructions", None)
            base["model"] = getattr(defn, "model", None)
            tools = getattr(defn, "tools", None) or []
            base["tools"] = [{"type": getattr(t, "type", None)} for t in tools]
        return base


@mcp.tool()
def create_conversation(initial_message: str | None = None) -> dict[str, Any]:
    """Create a new conversation in Foundry, optionally seeded with a user message.

    Returns `{conversation_id}`. Pair with `invoke_agent` to run a Foundry agent
    on the conversation.
    """
    with _project() as project:
        openai_client = _openai(project)
        if initial_message:
            items = [{"type": "message", "role": "user", "content": initial_message}]
            conv = openai_client.conversations.create(items=items)
        else:
            conv = openai_client.conversations.create()
        return {"conversation_id": conv.id}


@mcp.tool()
def append_message(
    conversation_id: str,
    content: str,
    role: str = "user",
) -> dict[str, Any]:
    """Append a message to an existing conversation. Role is typically 'user'."""
    with _project() as project:
        openai_client = _openai(project)
        items = [{"type": "message", "role": role, "content": content}]
        openai_client.conversations.items.create(
            conversation_id=conversation_id,
            items=items,
        )
        return {"conversation_id": conversation_id, "added": 1, "role": role}


@mcp.tool()
def invoke_agent(agent_name: str, conversation_id: str) -> dict[str, Any]:
    """Run a Foundry agent on an existing conversation and return its response.

    Uses the OpenAI Responses API with `agent_reference` pointing at the named agent.
    """
    with _project() as project:
        openai_client = _openai(project)
        response = openai_client.responses.create(
            conversation=conversation_id,
            extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
        )
        return {
            "conversation_id": conversation_id,
            "response_id": getattr(response, "id", None),
            "status": getattr(response, "status", None),
            "output_text": getattr(response, "output_text", None) or "",
        }


@mcp.tool()
def list_conversation(conversation_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """List items in a conversation — messages, tool calls, agent outputs."""
    with _project() as project:
        openai_client = _openai(project)
        items = openai_client.conversations.items.list(
            conversation_id=conversation_id,
            limit=limit,
        )
        rows: list[dict[str, Any]] = []
        for it in items:
            rows.append({
                "id": getattr(it, "id", None),
                "type": getattr(it, "type", None),
                "role": getattr(it, "role", None),
                "content": getattr(it, "content", None),
                "created_at": getattr(it, "created_at", None),
            })
        return rows


@mcp.tool()
def quick_ask(agent_name: str, prompt: str) -> dict[str, Any]:
    """One-shot: create a conversation seeded with `prompt`, invoke `agent_name`,
    return just the final output text."""
    with _project() as project:
        openai_client = _openai(project)
        conv = openai_client.conversations.create(
            items=[{"type": "message", "role": "user", "content": prompt}],
        )
        response = openai_client.responses.create(
            conversation=conv.id,
            extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
        )
        return {
            "conversation_id": conv.id,
            "response_id": getattr(response, "id", None),
            "status": getattr(response, "status", None),
            "answer": getattr(response, "output_text", None) or "",
        }


if __name__ == "__main__":
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))
    mcp.settings.host = host
    mcp.settings.port = port
    status = PROJECT_ENDPOINT or "MISSING — set FOUNDRY_PROJECT_ENDPOINT"
    print(
        f"[microsoft-foundry-agents-mcp] Streamable HTTP listening on http://{host}:{port}/mcp",
        flush=True,
    )
    print(f"  Project endpoint: {status}", flush=True)
    mcp.run(transport="streamable-http")
