# Community MCP Servers (in this repo)

Docker-first MCP servers for Microsoft services that live inside this repository.
Each subfolder is a self-contained, production-grade reference implementation.

| Server | Docker image | What it exposes |
| ------ | ------------ | --------------- |
| [`azure-resource-graph-mcp`](./azure-resource-graph-mcp/) | `ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/azure-resource-graph-mcp:latest` | Read-only Azure inventory via Resource Graph + KQL. |
| [`microsoft-learn-search-mcp`](./microsoft-learn-search-mcp/) | `ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/microsoft-learn-search-mcp:latest` | Search Microsoft Learn docs + fetch articles as Markdown. No auth. |

> 🚧 More servers land iteratively. Good candidates on the roadmap: `github-models-mcp`, `azure-openai-deployments-mcp`. **PRs welcome** — see the [contribution guide](../CONTRIBUTING.md).

## Conventions

Every server in this directory follows the same contract so you can mix-and-match them:

- **Streamable HTTP** transport on `/mcp`, default port `8000`.
- **Non-root** container user.
- **Multi-arch** (`linux/amd64` + `linux/arm64`) image on GHCR with SBOM + build provenance.
- **Read-only by default** (unless the service *is* about writes — in which case, write operations are opt-in via env vars and documented upfront).
- **`DefaultAzureCredential`-style auth** wherever an Azure-native SDK exists.
- **Host allow-list** for DNS-rebinding protection — accepts `MCP_ALLOWED_HOSTS` comma-separated overrides for reverse-proxy deployments.

## Running more than one at a time

Combine them with a single `compose.yaml`:

```yaml
services:
  resource-graph:
    image: ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/azure-resource-graph-mcp:latest
    ports: ["8001:8000"]
    environment:
      AZURE_CLIENT_ID: ${AZURE_CLIENT_ID}
      AZURE_TENANT_ID: ${AZURE_TENANT_ID}
      AZURE_CLIENT_SECRET: ${AZURE_CLIENT_SECRET}

  # Add more servers here as they land — each gets its own host port
```

Point your MCP client at each `http://localhost:<port>/mcp`.
