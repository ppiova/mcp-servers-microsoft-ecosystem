# Microsoft Graph MCP Server

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Streamable_HTTP-black)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![GHCR](https://img.shields.io/badge/GHCR-ghcr.io%2Fppiova%2Fmcp--servers--microsoft--ecosystem%2Fms--graph--mcp-181717?logo=github&logoColor=white)](https://github.com/ppiova/mcp-servers-microsoft-ecosystem/pkgs/container/mcp-servers-microsoft-ecosystem%2Fms-graph-mcp)

A **read-only** MCP server that exposes **Microsoft Graph** for the **IT-admin / security / compliance** angle: tenant inventory of users, groups, applications, service principals, group memberships and directory role assignments. App-only auth, predictable tool surface, ~100 MB image.

> **Why this server when there are already several Graph MCP servers?**
> Existing community servers focus on the **end-user** angle of Graph -- Outlook mail, calendar, Teams chats, OneDrive, SharePoint. This one focuses on the **directory & identity inventory** angle: "what's in my tenant, who has admin, what apps did we register, which guests showed up, which service principals exist". App-only auth, no per-user delegation needed.

---

## Tools exposed

| Tool                                | Args                                              | What it does                                                       |
| ----------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------ |
| `get_tenant_overview`               | --                                                | Snapshot counts of users, groups, applications, service principals.|
| `list_users`                        | `filter_query?, search?, top=50`                  | Directory users with `$filter` / `$search`.                        |
| `get_user`                          | `upn_or_id: str`                                  | Profile + manager + assigned licenses.                             |
| `list_groups`                       | `filter_query?, top=50`                           | Security and Microsoft 365 groups.                                 |
| `list_group_members`                | `group_id: str, top=50`                           | Direct members of a group.                                         |
| `list_applications`                 | `filter_query?, top=50`                           | App registrations in the tenant.                                   |
| `list_service_principals`           | `filter_query?, top=50`                           | Service principals (apps + managed identities).                    |
| `list_directory_role_assignments`   | `top=50`                                          | Active directory role assignments (admin roles).                   |

All tools cap a single Graph page at 100 results -- v1 does not follow `@odata.nextLink`. Use `filter_query` / `search` to narrow the result set.

---

## Example natural-language questions the agent can now answer

> "How many users, groups and registered apps are in this tenant?"
>
> "List all guest users created after 2026-01-01."
>
> "Who has the Global Administrator role?"
>
> "Show me the service principals that don't require app-role assignment."
>
> "Which Microsoft 365 groups exist and how many members does each have?"
>
> "Give me Pablo Piovano's manager and license assignments."

---

## Auth

The server uses `DefaultAzureCredential` from `azure-identity` (the async variant), which resolves in this order:

1. `AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_CLIENT_SECRET` env vars *(service principal -- recommended for containers)*
2. Azure Managed Identity *(when deployed to App Service / Container Apps / AKS)*

### Required Microsoft Graph **application permissions** (admin consent)

| Permission                       | Tools that need it                                  |
| -------------------------------- | --------------------------------------------------- |
| `Directory.Read.All`             | overview, users, groups, applications, SPs, members |
| `RoleManagement.Read.Directory`  | `list_directory_role_assignments`                   |

Grant these on the **app registration** that backs `AZURE_CLIENT_ID` and click **Grant admin consent for &lt;tenant&gt;** in the Azure portal. Without admin consent the calls will return `Authorization_RequestDenied` and the corresponding tool response will include an `*_error` field (or raise).

> The server only performs **read** operations -- it has no tools that mutate directory data. Even so, prefer `Directory.Read.All` over the broader `Directory.ReadWrite.All`.

---

## Run with Docker

### Option A -- Service principal env vars (recommended)

```bash
docker run --rm -p 8000:8000 \
  -e AZURE_TENANT_ID=<tenant-id> \
  -e AZURE_CLIENT_ID=<app-id> \
  -e AZURE_CLIENT_SECRET=<secret> \
  ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/ms-graph-mcp:latest
```

### Option B -- Build locally

```bash
cd servers/ms-graph-mcp
docker build -t ms-graph-mcp .
docker run --rm -p 8000:8000 \
  -e AZURE_TENANT_ID=<tenant-id> \
  -e AZURE_CLIENT_ID=<app-id> \
  -e AZURE_CLIENT_SECRET=<secret> \
  ms-graph-mcp
```

The server listens on **Streamable HTTP** at `http://localhost:8000/mcp`.

---

## Debug with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
# Connect to  http://localhost:8000/mcp   (transport: streamable-http)
```

You'll see all 8 tools and can call them directly to inspect Graph responses before wiring the server into an agent.

---

## Use from Microsoft Agent Framework (.NET)

```csharp
using ModelContextProtocol.Client;

var transport = new SseClientTransport(new SseClientTransportOptions
{
    Endpoint = new Uri("http://localhost:8000/mcp"),
    Name = "ms-graph",
});
await using var mcp = await McpClientFactory.CreateAsync(transport);

var tools = await mcp.ListToolsAsync();
var agent = chatClient.CreateAIAgent(
    name: "TenantInsightsAgent",
    instructions: "Answer tenant directory and identity questions using the Microsoft Graph MCP tools.",
    tools: [.. tools.Cast<AITool>()]);

Console.WriteLine(await agent.RunAsync("Who has the Global Administrator role in our tenant?"));
```

---

## Use from Claude Desktop / Copilot / Cursor

Add to your MCP client config (example for Claude Desktop):

```json
{
  "mcpServers": {
    "ms-graph": {
      "url": "http://localhost:8000/mcp",
      "transport": "streamable-http"
    }
  }
}
```

---

## Security notes

- **Read-only by design.** The toolset doesn't expose write/update/delete verbs. The server cannot be coerced into mutating directory data.
- **Permissions respected.** Tools fail gracefully when the underlying Graph permission is missing -- no escalation possible.
- **Streamable-HTTP + host allow-list.** Protected against DNS-rebinding by default. Behind a reverse proxy? Add hostnames to `MCP_ALLOWED_HOSTS` (comma-separated).
- **Don't expose `:8000` to the public internet.** There's no authentication in the transport by design -- put it behind a private network, an authenticated proxy (APIM, Application Gateway), or keep it local.
- **Pagination is capped at 100.** This is a deliberate v1 simplification. If you need more, use `filter_query` to narrow the slice of the directory you care about.

---

## Roadmap (v2 ideas)

- Pagination via `@odata.nextLink` for tenants beyond 100 of any entity type.
- `list_recent_sign_ins` and `list_recent_audit_events` once `AuditLog.Read.All` is well-documented as opt-in.
- Per-user PIM-eligible role assignment lookup.

---

## License

[MIT](../../LICENSE) -- by [Pablo Piovano](https://github.com/ppiova).
