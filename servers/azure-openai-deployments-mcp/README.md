# Azure OpenAI Deployments MCP Server

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Streamable_HTTP-black)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

A **read-only** MCP server that inventories every **Azure OpenAI account** + **model deployment** + **regional quota** across the subscriptions the caller can see.

Answers questions like:

> *"Where is `gpt-4o-mini` deployed and what's the SKU capacity?"*
>
> *"Do I still have S0 quota left for `gpt-4.1` in `eastus2`?"*
>
> *"Which deployments have the relaxed RAI policy?"*
>
> *"¿Qué modelos tengo versión 2025 ya desplegados y en qué sub?"*

---

## Why this alongside the official [`Azure/azure-mcp`](https://github.com/Azure/azure-mcp)?

The official Azure MCP covers a huge surface (230+ tools). Use **this one** when:

- 💰 You specifically need a **FinOps / model-ops** focus — quotas, capacities, versions.
- 🪶 You want a **small, fast, single-purpose** image (~110 MB Python).
- 🧑‍🎓 You want **~200 lines of readable source** that you can fork for a different Azure service (same SDK patterns work for Azure AI Search, Azure AI Foundry hubs, etc.).

---

## Tools exposed

| Tool                     | Args                                                         | What it does                                          |
| ------------------------ | ------------------------------------------------------------ | ----------------------------------------------------- |
| `list_subscriptions`     | —                                                            | Subs the identity can see.                            |
| `list_openai_accounts`   | `subscription_id?`                                           | All `kind='OpenAI'` accounts (across subs if omitted).|
| `list_deployments`       | `subscription_id, resource_group, account_name`              | Model, SKU, capacity, RAI policy per deployment.      |
| `get_deployment`         | `subscription_id, resource_group, account_name, deployment_name` | Full detail incl. rate limit + capabilities.      |
| `list_all_deployments`   | `subscription_id?, location?`                                | Flat sweep across every account, optional region.     |
| `list_usages`            | `subscription_id, location`                                  | Quota usage per model/SKU in a region.                |

---

## Auth

Uses `DefaultAzureCredential` — same chain as the rest of this repo:

1. `AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_CLIENT_SECRET` *(service principal — great for containers & CI)*
2. `~/.azure/` mounted into the container *(local dev with `az login`)*
3. Azure Managed Identity *(when hosted in Azure)*

**Grant only `Reader`** on the subscriptions/RGs you want introspected. The server exposes no write operations.

---

## Run with Docker

### Service principal (easiest inside containers)

```bash
docker run --rm -p 8000:8000 \
  -e AZURE_CLIENT_ID=<app-id> \
  -e AZURE_TENANT_ID=<tenant-id> \
  -e AZURE_CLIENT_SECRET=<secret> \
  ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/azure-openai-deployments-mcp:latest
```

### Local dev with `az login`

```bash
docker run --rm -p 8000:8000 \
  -v "$HOME/.azure:/app/.azure:ro" \
  -e AZURE_CONFIG_DIR=/app/.azure \
  ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/azure-openai-deployments-mcp:latest
```

### Build locally

```bash
cd servers/azure-openai-deployments-mcp
docker build -t azure-openai-deployments-mcp .
docker run --rm -p 8000:8000 azure-openai-deployments-mcp
```

Listens on **Streamable HTTP** at `http://localhost:8000/mcp`.

---

## From Microsoft Agent Framework (.NET)

```csharp
using ModelContextProtocol.Client;

var transport = new SseClientTransport(new SseClientTransportOptions
{
    Endpoint = new Uri("http://localhost:8000/mcp"),
    Name = "azure-openai-deployments",
});
await using var mcp = await McpClientFactory.CreateAsync(transport);

var agent = chat.CreateAIAgent(
    name: "FinOpsAssistant",
    instructions:
        "You help users answer FinOps and capacity questions about their Azure OpenAI " +
        "estate. Start with `list_all_deployments`. Use `list_usages` for region-level quota.",
    tools: [.. (await mcp.ListToolsAsync()).Cast<AITool>()]);

Console.WriteLine(await agent.RunAsync(
    "¿Qué deployments de gpt-4o-mini tengo y cuánta capacidad queda en eastus2?"));
```

---

## Debug with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
# http://localhost:8000/mcp   (transport: streamable-http)
```

Try:

```
list_all_deployments  {}
list_all_deployments  { "location": "eastus2" }
list_usages           { "subscription_id": "...", "location": "eastus2" }
```

---

## Security notes

- **Read-only by design** — no create/update/delete verbs exposed.
- **RBAC respected** — scoped to what the identity can see.
- **DNS-rebinding protection** — `MCP_ALLOWED_HOSTS` env var appends extra allowed Host headers (for reverse-proxy deployments).
- **Don't expose `:8000` publicly** without auth in front (APIM, Application Gateway, or similar).

---

## License

[MIT](../../LICENSE) — by [Pablo Piovano](https://github.com/ppiova).
