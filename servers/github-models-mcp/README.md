# GitHub Models MCP Server

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Streamable_HTTP-black)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Free tier](https://img.shields.io/badge/GitHub_Models-free_tier-24292F?logo=github&logoColor=white)](https://github.com/marketplace/models)

An MCP server that exposes the **free-tier [GitHub Models](https://github.com/marketplace/models)** catalog and inference endpoints as MCP tools. Bring OpenAI GPT-4.1, Microsoft Phi-4, Meta Llama 3.3, Mistral, Cohere, DeepSeek and more to any MCP-compatible client — **for free**, with just a GitHub token.

> **Key idea**: let your main agent (Azure OpenAI, Claude, etc.) delegate tasks to cheaper / experimental models via MCP — without writing a model-router from scratch.

---

## Use cases

| Pattern            | Why you'd use it                                                            |
| ------------------ | --------------------------------------------------------------------------- |
| **Routing**        | Send summaries / classifications to `microsoft/Phi-4` instead of GPT-4o.    |
| **Fallback**       | If Azure OpenAI hits a quota wall, retry on GitHub Models.                  |
| **A/B compare**    | Ask the same question to 3 publishers — let your agent pick the best.      |
| **Discovery**      | Live query *"which models support images? which are under 10B params?"*     |
| **Prototyping**    | Try brand-new models the day they land on GitHub Models with zero cost.    |

---

## Tools exposed

| Tool              | Args                                                     | Auth        | What it does                                                |
| ----------------- | -------------------------------------------------------- | ----------- | ----------------------------------------------------------- |
| `list_models`     | `publisher?`                                             | none        | Live catalog, optional publisher filter.                    |
| `get_model_info`  | `model_id`                                               | none        | Full catalog entry for a single model.                      |
| `chat`            | `model, prompt, system?, max_tokens?, temperature?`      | GITHUB_TOKEN | Single-turn chat completion.                               |
| `compare_models`  | `models[], prompt, system?, max_tokens?, temperature?`   | GITHUB_TOKEN | Same prompt → N models → all responses in one call.        |

---

## Auth

- **Catalog browsing is public** — `list_models` and `get_model_info` work without a token.
- **Inference** (`chat`, `compare_models`) requires a GitHub PAT with the `models:read` scope. Pass it as the `GITHUB_TOKEN` env var.

Create a token at → **GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens** → scope: `Models (read-only)`.

---

## Run with Docker

### Full access (catalog + inference)

```bash
docker run --rm -p 8000:8000 \
  -e GITHUB_TOKEN=ghp_yourFinegrainedTokenWithModelsReadScope \
  ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/github-models-mcp:latest
```

### Catalog-only (no token)

```bash
docker run --rm -p 8000:8000 \
  ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/github-models-mcp:latest
```

`chat` and `compare_models` will return a clear "GITHUB_TOKEN missing" error. `list_models` and `get_model_info` keep working.

### Build locally

```bash
cd servers/github-models-mcp
docker build -t github-models-mcp .
docker run --rm -p 8000:8000 -e GITHUB_TOKEN=$GITHUB_TOKEN github-models-mcp
```

The server listens on **Streamable HTTP** at `http://localhost:8000/mcp`.

---

## Example: pair with Microsoft Agent Framework (.NET)

Give your main Azure OpenAI agent a **delegation tool**:

```csharp
using ModelContextProtocol.Client;

var ghModels = await McpClientFactory.CreateAsync(
    new SseClientTransport(new SseClientTransportOptions
    {
        Endpoint = new Uri("http://localhost:8000/mcp"),
        Name = "github-models",
    }));

var agent = chatClient.CreateAIAgent(
    name: "RouterAgent",
    instructions:
        "You are a Router. For simple classifications, summaries or extractions, " +
        "prefer calling the `chat` tool with `microsoft/Phi-4` or `mistral-ai/Mistral-Small` " +
        "rather than answering directly. For hard reasoning, answer yourself with GPT-4o. " +
        "For critical questions use `compare_models` with 3 top-tier models and pick the best.",
    tools: [.. (await ghModels.ListToolsAsync()).Cast<AITool>()]);

Console.WriteLine(await agent.RunAsync(
    "Classify this customer email as (billing|support|sales|other) and extract the customer's name:\n\n---\nHi, I'm John Smith. My last invoice was charged twice — can you refund?"));
```

---

## Debug with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
# Connect to http://localhost:8000/mcp  (transport: streamable-http)
```

Try these:

```jsonc
// No token needed:
list_models       { "publisher": "OpenAI" }
get_model_info    { "model_id": "openai/gpt-4.1-mini" }

// Requires GITHUB_TOKEN:
chat              { "model": "microsoft/Phi-4", "prompt": "Explain MCP in 2 sentences." }
compare_models    { "models": ["openai/gpt-4.1-mini", "microsoft/Phi-4", "mistral-ai/Mistral-Small"],
                    "prompt": "What is tail latency?" }
```

---

## Notes & limits

- **Free tier = rate limits.** GitHub Models has per-request, per-day and per-token caps. The server surfaces API errors as-is — handle them in your agent's retry logic.
- **Region**: GitHub Models inference runs on Microsoft infrastructure (powered by Azure AI Foundry). Latency from LATAM / EU is usually fine but not guaranteed.
- **Privacy**: free-tier prompts may be used by publishers per [GitHub's terms](https://docs.github.com/site-policy/github-terms/github-terms-for-additional-products-and-features#models). Don't send PII/regulated data via the free tier.
- **No streaming** — the MCP tool returns the full completion. For streaming, connect the model directly from your agent without routing through this MCP.

---

## Security notes

- **No write verbs exposed**, but `chat` consumes your free-tier quota. Limit who can hit this server.
- **Secrets**: pass `GITHUB_TOKEN` via env var or Docker secret — not baked into images.
- **DNS-rebinding allow-list** — `MCP_ALLOWED_HOSTS` appends extra allowed hostnames.
- **Don't expose `:8000` publicly** — put it behind an authenticated reverse proxy or keep it local.

---

## License

[MIT](../../LICENSE) — by [Pablo Piovano](https://github.com/ppiova).
