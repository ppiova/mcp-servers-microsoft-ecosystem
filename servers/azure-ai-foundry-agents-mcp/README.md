# Azure AI Foundry Agents MCP Server

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Streamable_HTTP-black)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Azure AI Foundry](https://img.shields.io/badge/Azure_AI_Foundry-agents-0078D4?logo=microsoft&logoColor=white)](https://learn.microsoft.com/en-us/azure/ai-foundry/)

A bridge that exposes your **Azure AI Foundry agents** to any MCP-compatible client — Claude, Copilot, Cursor, Microsoft Agent Framework.

> **The pattern**: you design specialized domain agents in **Foundry Portal** (HR agent, KB Q&A agent, code-review agent — each with its own model, tools and grounding). This server hands every one of them to any MCP client as a single invokable tool surface. Your orchestrator agent anywhere in the stack can now delegate work to them.

---

## When to use this

- You already have Foundry agents deployed (with their knowledge grounding, tools, RAI policies) and want to use them from outside Foundry.
- You want **multi-agent routing** without rebuilding the hierarchy in another framework.
- You run a main agent in **Claude Desktop / Copilot / Agent Framework / Cursor** and want it to *"hand off"* tasks to Foundry agents.
- You need a **standard MCP surface** for your Foundry estate so teams can swap clients freely.

---

## Tools exposed

| Tool             | Args                                                | What it does                                                  |
| ---------------- | --------------------------------------------------- | ------------------------------------------------------------- |
| `list_agents`    | —                                                   | All agents in the project.                                    |
| `get_agent`      | `agent_id`                                          | Full metadata — instructions, tools, model.                   |
| `create_thread`  | —                                                   | New conversation thread; returns `{thread_id}`.               |
| `add_message`    | `thread_id, content, role="user"`                   | Post to a thread.                                             |
| `run_agent`      | `thread_id, agent_id, timeout_seconds=120`          | Execute agent on thread; waits for terminal state.            |
| `list_messages`  | `thread_id, limit=20`                               | Last N messages on a thread.                                  |
| `quick_ask`      | `agent_id, prompt, timeout_seconds=120`             | **One-shot**: thread + run + return assistant's answer.       |

---

## Config

Set the project endpoint as an env var:

```bash
AZURE_AI_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project-name>
```

(You'll find this in Foundry Portal → your project → **Overview** → *"Project details"*.)

### Auth

`DefaultAzureCredential`:

1. Service principal env vars (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`).
2. `~/.azure/` mounted from host (`az login` first).
3. Managed Identity in Azure-hosted compute.

The identity needs the **"Azure AI User"** role on the Foundry project.

---

## Run with Docker

### Service principal (containers / CI)

```bash
docker run --rm -p 8000:8000 \
  -e AZURE_AI_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project> \
  -e AZURE_CLIENT_ID=<app-id> \
  -e AZURE_TENANT_ID=<tenant-id> \
  -e AZURE_CLIENT_SECRET=<secret> \
  ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/azure-ai-foundry-agents-mcp:latest
```

### Local with `az login`

```bash
docker run --rm -p 8000:8000 \
  -e AZURE_AI_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project> \
  -v "$HOME/.azure:/app/.azure:ro" \
  -e AZURE_CONFIG_DIR=/app/.azure \
  ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/azure-ai-foundry-agents-mcp:latest
```

The server listens on **Streamable HTTP** at `http://localhost:8000/mcp`.

---

## Flow: delegate from a Microsoft Agent Framework orchestrator

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
        "For each user request, pick the best agent and use `quick_ask` with their id and the " +
        "refined prompt. Quote the agent's answer back to the user.",
    tools: [.. (await foundry.ListToolsAsync()).Cast<AITool>()]);

Console.WriteLine(await orchestrator.RunAsync(
    "The user wants a vacation policy answer and a travel cost estimate. " +
    "Delegate each sub-task to the right Foundry agent."));
```

---

## From Claude Desktop

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

Now Claude can call your Foundry HR-agent, KB-agent, etc. directly by name.

---

## Debug with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
# http://localhost:8000/mcp (transport: streamable-http)
```

Try:

```
list_agents    {}
quick_ask      { "agent_id": "<asst_...>", "prompt": "Dame tres ideas de campaña para Q2." }
create_thread  {}
```

---

## Notes & limits

- **Supported features** depend on the agent you're calling — if a Foundry agent uses code interpreter, file search, or custom tools, those run server-side in Foundry. This MCP is just the invocation wire.
- **`requires_action`** runs (when an agent asks for tool outputs) aren't auto-handled here — add that logic in a follow-up if you need it.
- **RBAC** — the MCP identity can only invoke agents it has read access to in Foundry.
- **Costs** — each `run_agent` / `quick_ask` consumes tokens on the agent's underlying Azure OpenAI deployment. Monitor via the [`azure-openai-deployments-mcp`](../azure-openai-deployments-mcp/) server in this same repo.

---

## Security notes

- Expose only on private networks or behind an authenticated proxy.
- Never bake `AZURE_CLIENT_SECRET` into the image; always pass via env vars or Docker secrets.
- DNS-rebinding allow-list — append extra hostnames via `MCP_ALLOWED_HOSTS` (comma-separated) for reverse-proxy scenarios.

---

## License

[MIT](../../LICENSE) — by [Pablo Piovano](https://github.com/ppiova).
