# Azure Resource Graph MCP Server

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Streamable_HTTP-black)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![GHCR](https://img.shields.io/badge/GHCR-ghcr.io%2Fppiova%2Fmcp--servers--microsoft--ecosystem%2Fazure--resource--graph--mcp-181717?logo=github&logoColor=white)](https://github.com/ppiova/mcp-servers-microsoft-ecosystem/pkgs/container/mcp-servers-microsoft-ecosystem%2Fazure-resource-graph-mcp)

A **read-only**, **lightweight** MCP server that exposes your Azure estate through **Azure Resource Graph (KQL)** — powerful natural-language inventory for any MCP-compatible client (Claude, Copilot, VS Code, Agent Framework, Cursor…).

> **Why not use the [official `Azure/azure-mcp`](https://github.com/Azure/azure-mcp)?** You should — when you need its 230+ tools across 45 services. Use **this** one when you only need **inventory and ad-hoc KQL queries**, want a **smaller image** (~100 MB), a **Python** stack you can read in one sitting, and **zero-configuration Docker** deployment.

---

## Tools exposed

| Tool                       | Args                                                  | What it does                                      |
| -------------------------- | ----------------------------------------------------- | ------------------------------------------------- |
| `list_subscriptions`       | —                                                     | Every sub the signed-in identity can see.         |
| `query_resources`          | `query: str, subscription_ids?, top=100`              | Run any KQL query against Resource Graph.         |
| `list_resource_groups`     | `subscription_id: str`                                | RGs with location + tags.                         |
| `list_vms`                 | `subscription_id?, location?`                         | VMs w/ size, OS, power state.                     |
| `list_resources_by_type`   | `resource_type: str, subscription_id?`                | All resources of a given ARM type.                |
| `list_distinct_types`      | `subscription_id?`                                    | Types present + counts (great for exploration).   |

---

## Example natural-language questions the agent can now answer

> "Which VMs do I have running in `eastus2` with more than 16 GB of RAM?"
>
> "List all storage accounts across all subscriptions where replication is LRS and the region is not westeurope."
>
> "Give me the 5 subscriptions with the most resources and the 3 most used regions."
>
> "Find every resource tagged `env=prod` that doesn't have an `owner` tag."

Those all collapse into a single `query_resources(...)` call with KQL — no custom tools required.

---

## Auth

The server uses `DefaultAzureCredential`, which resolves in this order:

1. `AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_CLIENT_SECRET` env vars *(service principal — good for containers & CI)*
2. `~/.azure/` from your host *(mounted into the container — good for local dev after `az login`)*
3. Azure Managed Identity *(when deployed to App Service / Container Apps / AKS)*

The server only performs **read** operations (Resource Graph queries + subscription list). Grant the identity **Reader** on the subscriptions you want visible — nothing more.

---

## Run with Docker

### Option A — Service principal (easiest inside containers)

```bash
docker run --rm -p 8000:8000 \
  -e AZURE_CLIENT_ID=<app-id> \
  -e AZURE_TENANT_ID=<tenant-id> \
  -e AZURE_CLIENT_SECRET=<secret> \
  ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/azure-resource-graph-mcp:latest
```

### Option B — Mount your `az login` session (local dev)

After `az login` on your host:

```bash
docker run --rm -p 8000:8000 \
  -v "$HOME/.azure:/app/.azure:ro" \
  -e AZURE_CONFIG_DIR=/app/.azure \
  ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/azure-resource-graph-mcp:latest
```

### Option C — Build locally

```bash
cd servers/azure-resource-graph-mcp
docker build -t azure-resource-graph-mcp .
docker run --rm -p 8000:8000 azure-resource-graph-mcp
```

The server listens on **Streamable HTTP** at `http://localhost:8000/mcp`.

---

## Debug with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
# Connect to  http://localhost:8000/mcp   (transport: streamable-http)
```

You'll see the 6 tools, can call them directly, and inspect KQL responses before wiring the server into an agent.

---

## Use from Microsoft Agent Framework (.NET)

```csharp
using ModelContextProtocol.Client;

var transport = new SseClientTransport(new SseClientTransportOptions
{
    Endpoint = new Uri("http://localhost:8000/mcp"),
    Name = "azure-resource-graph",
});
await using var mcp = await McpClientFactory.CreateAsync(transport);

var tools = await mcp.ListToolsAsync();
var agent = chatClient.CreateAIAgent(
    name: "AzureInventoryAgent",
    instructions: "Answer questions about the user's Azure estate using the MCP tools.",
    tools: [.. tools.Cast<AITool>()]);

Console.WriteLine(await agent.RunAsync("List all VMs in eastus2 bigger than Standard_D8s_v5."));
```

See the full end-to-end stack in **[`ppiova/mcp-docker-starter`](https://github.com/ppiova/mcp-docker-starter)**.

---

## Use from Claude Desktop / Copilot / Cursor

Add to your MCP client config (example for Claude Desktop):

```json
{
  "mcpServers": {
    "azure-resource-graph": {
      "url": "http://localhost:8000/mcp",
      "transport": "streamable-http"
    }
  }
}
```

---

## Security notes

- **Read-only by design.** This server never performs writes, deletes, or rolls out ARM templates. It can't be instructed to — the toolset doesn't expose those verbs.
- **RBAC respected.** Results are scoped to what the credential can see. Don't grant more than `Reader`.
- **Streamable-HTTP + host allow-list.** Protected against DNS-rebinding by default. Behind a reverse proxy? Add hostnames to `MCP_ALLOWED_HOSTS` (comma-separated).
- **Don't expose `:8000` to the public internet.** There's no authentication in the transport by design — put it behind a private network, an authenticated proxy (APIM, Application Gateway), or keep it local.

---

## License

[MIT](../../LICENSE) — by [Pablo Piovano](https://github.com/ppiova).
