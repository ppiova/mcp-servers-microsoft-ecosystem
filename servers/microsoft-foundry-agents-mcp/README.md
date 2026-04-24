# Microsoft Foundry Agents MCP Server

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Streamable_HTTP-black)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Microsoft Foundry](https://img.shields.io/badge/Microsoft_Foundry-SDK_2.x-5C2D91?logo=microsoft&logoColor=white)](https://learn.microsoft.com/en-us/azure/foundry/)

A bridge that exposes your **[Microsoft Foundry](https://devblogs.microsoft.com/foundry/)** (formerly *Azure AI Foundry*) hosted agents to any MCP-compatible client — Claude, Copilot, Cursor, Microsoft Agent Framework — using the **v2 Responses API** shipped with `azure-ai-projects` 2.0 (March 2026 GA).

> **The pattern**: you design specialized domain agents in **Foundry Portal** (HR agent, KB Q&A agent, code-review agent — each with its own model, tools and grounding). This server makes every one of them a callable tool for any MCP client.

---

## ⚠️ Migrated to Microsoft Foundry SDK 2.x

This server was rebuilt in April 2026 for the GA **2.0** SDK, which replaces the old *threads + messages + runs* model with **conversations + responses + `agent_reference`**:

| Old (1.x, now removed) | New (2.0 GA)                                                          |
| ---------------------- | --------------------------------------------------------------------- |
| `project.agents.threads.create()` | `openai_client.conversations.create()`                     |
| `project.agents.messages.create(thread_id, role, content)` | `openai_client.conversations.items.create(conversation_id, items=[...])` |
| `project.agents.runs.create_and_process(thread_id, agent_id)` | `openai_client.responses.create(conversation, extra_body={"agent_reference": {...}})` |
| `model_id` parameter | `model` parameter                                                  |
| `azure-ai-agents` dep | Rolled into `azure-ai-projects`                                      |

See [Python 2026 Significant Changes Guide](https://learn.microsoft.com/en-us/agent-framework/support/upgrade/python-2026-significant-changes) for the full migration notes.

---

## Tools exposed

| Tool                  | Args                                           | What it does                                             |
| --------------------- | ---------------------------------------------- | -------------------------------------------------------- |
| `list_agents`         | —                                              | All agents in the project (name + latest version).       |
| `get_agent`           | `agent_name`                                   | Instructions, model, tools for the latest version.       |
| `create_conversation` | `initial_message?`                             | Returns `{conversation_id}`.                             |
| `append_message`      | `conversation_id, content, role="user"`        | Adds a message to a conversation.                        |
| `invoke_agent`        | `agent_name, conversation_id`                  | Runs the agent; returns `{output_text, status, ...}`.    |
| `list_conversation`   | `conversation_id, limit=20`                    | Conversation items (messages, tool calls, outputs).      |
| `quick_ask`           | `agent_name, prompt`                           | **One-shot**: create + invoke → `{answer}`.              |

---

## Config

### Environment

| Var | Required | Notes |
|-----|----------|-------|
| `FOUNDRY_PROJECT_ENDPOINT` | ✅ | Full project URL — find it in Foundry Portal → your project → **Overview** |
| `AZURE_AI_PROJECT_ENDPOINT` / `PROJECT_ENDPOINT` | — | Legacy aliases, still accepted |
| Azure AD creds *(one of)* | ✅ | `AZURE_CLIENT_ID` + `AZURE_TENANT_ID` + `AZURE_CLIENT_SECRET`, or mount `~/.azure` from a host with `az login` |

Example endpoint format:

```
https://<resource>.services.ai.azure.com/api/projects/<project-name>
```

### Azure RBAC

`DefaultAzureCredential` — identity needs the **"Azure AI User"** role on the Foundry project.

---

## Run with Docker

### Service principal (containers / CI)

```bash
docker run --rm -p 8000:8000 \
  -e FOUNDRY_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project> \
  -e AZURE_CLIENT_ID=<app-id> \
  -e AZURE_TENANT_ID=<tenant-id> \
  -e AZURE_CLIENT_SECRET=<secret> \
  ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/microsoft-foundry-agents-mcp:latest
```

### Local with `az login`

```bash
docker run --rm -p 8000:8000 \
  -e FOUNDRY_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project> \
  -v "$HOME/.azure:/app/.azure:ro" \
  -e AZURE_CONFIG_DIR=/app/.azure \
  ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/microsoft-foundry-agents-mcp:latest
```

The server listens on **Streamable HTTP** at `http://localhost:8000/mcp`.

---

## Use from Microsoft Agent Framework (.NET)

```csharp
using ModelContextProtocol.Client;

var foundry = await McpClientFactory.CreateAsync(
    new SseClientTransport(new SseClientTransportOptions
    {
        Endpoint = new Uri("http://localhost:8000/mcp"),
        Name = "foundry-agents",
    }));

var orchestrator = chatClient.CreateAIAgent(
    name: "Orchestrator",
    instructions:
        "You coordinate specialized Foundry agents. Call `list_agents` to see what's available. " +
        "For each user request, pick the best agent and use `quick_ask` with the agent name " +
        "and the refined prompt. Quote the agent's answer back to the user.",
    tools: [.. (await foundry.ListToolsAsync()).Cast<AITool>()]);

Console.WriteLine(await orchestrator.RunAsync(
    "The user wants a vacation policy answer and a travel cost estimate. " +
    "Delegate each sub-task to the right Foundry agent."));
```

---

## From Claude Desktop / Copilot / Cursor

```json
{
  "mcpServers": {
    "foundry-agents": {
      "url": "http://localhost:8000/mcp",
      "transport": "streamable-http"
    }
  }
}
```

---

## Debug with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
# http://localhost:8000/mcp (transport: streamable-http)
```

Try:

```
list_agents            {}
get_agent              { "agent_name": "your-agent" }
quick_ask              { "agent_name": "your-agent", "prompt": "Dame tres ideas de campaña para Q2." }
create_conversation    { "initial_message": "Hola" }
```

---

## Notes & limits

- **Tool execution, code interpreter, file search, grounding** — all run server-side in Foundry. This MCP is the invocation wire, not a re-implementation.
- **`requires_action`-style interactive tool calls** aren't round-tripped here; add that logic in your orchestrator if needed.
- **RBAC** — the MCP identity can only invoke agents it has read access to in Foundry.
- **Costs** — each `invoke_agent` / `quick_ask` consumes tokens on the agent's underlying model deployment. Monitor spend via the sibling [`azure-openai-deployments-mcp`](../azure-openai-deployments-mcp/) server.
- **Streaming** is not surfaced via this MCP (tools return the final response). For streaming, connect to the Foundry Responses endpoint directly.

---

## Security notes

- Expose only on private networks or behind an authenticated proxy.
- Never bake `AZURE_CLIENT_SECRET` into the image; pass via env vars or Docker secrets.
- DNS-rebinding allow-list — append extra hostnames via `MCP_ALLOWED_HOSTS` (comma-separated) for reverse-proxy scenarios.

---

## License

[MIT](../../LICENSE) — by [Pablo Piovano](https://github.com/ppiova).
