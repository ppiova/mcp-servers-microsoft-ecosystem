# Microsoft Learn Search MCP Server

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Streamable_HTTP-black)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![No auth](https://img.shields.io/badge/Auth-none-green)](./README.md)

A self-hostable MCP server that lets any LLM client **search Microsoft Learn documentation** and **pull full article content as Markdown**. Zero auth. Zero setup.

> *"Hey agent, find me the official Azure OpenAI rate-limit article and summarize it."*
>
> → Your agent calls `search("azure openai rate limits")` → picks the best hit → calls `get_article(url)` → answers with fresh, canonical Microsoft docs.

---

## Why a self-hosted version?

Microsoft runs a **hosted** endpoint at `microsoft.docs.mcp`. Use that when you can. Run **this** one when you need any of:

- 🏢 **Compliance / air-gapped** environments where external MCP endpoints are blocked.
- ⚡ **Low latency** for high-volume agent workflows (local network round-trip).
- 🐳 **Full control** over the stack, logging, and caching.
- 🧪 **Agent dev loops** where stability of a local container beats reaching out over the public internet.
- 🎓 **Learning** — the source is ~130 lines of Python you can read, fork and extend.

---

## Tools exposed

| Tool                 | Args                                         | What it does                                       |
| -------------------- | -------------------------------------------- | -------------------------------------------------- |
| `search`             | `query, locale="en-us", top=10, scope?`      | Top-N results from learn.microsoft.com/api/search  |
| `get_article`        | `url, max_chars=20000`                       | Fetches a Learn article and returns clean Markdown |
| `list_known_scopes`  | —                                            | Curated list of common product scopes for `search` |

The `scope` parameter restricts search to a product area — `"Azure"`, `"Azure AI Foundry"`, `".NET"`, `"Microsoft Fabric"`, `"Microsoft 365"`, `"Power Platform"`, `"Microsoft Graph"`, etc.

---

## Run with Docker

```bash
docker run --rm -p 8000:8000 \
  ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/microsoft-learn-search-mcp:latest
```

That's it. No secrets. No `.env`. Server listens on **Streamable HTTP** at `http://localhost:8000/mcp`.

### Build locally

```bash
cd servers/microsoft-learn-search-mcp
docker build -t microsoft-learn-search-mcp .
docker run --rm -p 8000:8000 microsoft-learn-search-mcp
```

---

## Example flows

### From Claude Desktop / Copilot / any MCP client

```json
{
  "mcpServers": {
    "microsoft-learn": {
      "url": "http://localhost:8000/mcp",
      "transport": "streamable-http"
    }
  }
}
```

Then ask:

> *"Using microsoft-learn, find the steps to assign a managed identity to an Azure Container Apps revision. Cite URLs."*

### From Microsoft Agent Framework (.NET)

```csharp
using ModelContextProtocol.Client;

var transport = new SseClientTransport(new SseClientTransportOptions
{
    Endpoint = new Uri("http://localhost:8000/mcp"),
    Name = "microsoft-learn",
});
await using var mcp = await McpClientFactory.CreateAsync(transport);

var agent = chatClient.CreateAIAgent(
    name: "LearnAssistant",
    instructions:
        "You ground every technical answer in Microsoft Learn. " +
        "Call `search` first; open the top 1–2 hits with `get_article`; cite URLs in the response.",
    tools: [.. (await mcp.ListToolsAsync()).Cast<AITool>()]);

Console.WriteLine(await agent.RunAsync(
    "¿Cómo deploy un Agent Framework sample a Azure Container Apps con managed identity?"));
```

---

## Debug with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
# Connect to http://localhost:8000/mcp  (transport: streamable-http)
```

Try these in the Inspector:

```
search  { "query": "azure openai rate limits", "top": 5 }
search  { "query": "copilot studio MCP extend agent", "scope": "Copilot Studio" }
get_article  { "url": "https://learn.microsoft.com/en-us/azure/ai-foundry/what-is-ai-foundry", "max_chars": 5000 }
list_known_scopes  {}
```

---

## Notes & limits

- **Public API**. Microsoft Learn's search endpoint doesn't document rate limits — be respectful. This image includes a descriptive `User-Agent` so Microsoft can identify traffic.
- **No caching built-in.** Add a reverse proxy with cache (NGINX / Varnish) in front if you're hammering common queries.
- **Locales**. Most Microsoft Learn content exists in `en-us`; other locales may have sparser coverage. The `locale` param accepts the standard codes (`en-us`, `es-es`, `pt-br`, `ja-jp`, `fr-fr`, …).
- **Article extraction** strips nav/footer/scripts and converts main content to Markdown via `markdownify`. It's not a perfect fidelity converter — tables with spans and some rich components may simplify.

---

## License

[MIT](../../LICENSE) — by [Pablo Piovano](https://github.com/ppiova).
