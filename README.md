# MCP Servers for the Microsoft Ecosystem

[![Awesome](https://awesome.re/badge-flat.svg)](https://awesome.re)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)
[![Updated](https://img.shields.io/github/last-commit/ppiova/mcp-servers-microsoft-ecosystem?label=updated&color=blue)](https://github.com/ppiova/mcp-servers-microsoft-ecosystem/commits/main)
[![Link check](https://github.com/ppiova/mcp-servers-microsoft-ecosystem/actions/workflows/links.yml/badge.svg)](https://github.com/ppiova/mcp-servers-microsoft-ecosystem/actions/workflows/links.yml)

> A community-curated catalog of **Model Context Protocol (MCP)** servers that connect AI agents to the **Microsoft ecosystem** — Azure, Microsoft 365, Fabric, Power Platform, GitHub, Copilot Studio, and developer tools.

This list complements [`microsoft/mcp`](https://github.com/microsoft/mcp) — the **official Microsoft MCP catalog** — by covering:

- ✅ Community implementations the official catalog doesn't include
- ✅ Opinionated organization by **service area**, **language**, and **Docker readiness**
- ✅ Clients, starters, learning resources, and security guidance
- ✅ Pointers to working samples you can clone and run today

> **New to MCP?** MCP is the open protocol — often called *"USB-C for AI agents"* — that lets any LLM client (Claude, GitHub Copilot, Cursor, VS Code, Copilot Studio, Agent Framework…) talk to any tool server through a single standard. Think of each server below as a **universal adapter** between AI and a specific Microsoft product.

---

## Contents

- [Official Microsoft MCP Servers](#official-microsoft-mcp-servers)
- [Azure](#azure)
- [Microsoft 365 & Graph](#microsoft-365--graph)
- [Fabric, Power BI & Data](#fabric-power-bi--data)
- [Power Platform & Copilot Studio](#power-platform--copilot-studio)
- [GitHub](#github)
- [Developer Tools & Microsoft Learn](#developer-tools--microsoft-learn)
- [Playwright & Browser Automation](#playwright--browser-automation)
- [MCP Clients in Microsoft Products](#mcp-clients-in-microsoft-products)
- [Community servers in this repo](#community-servers-in-this-repo)
- [Starters & Templates](#starters--templates)
- [Security & Governance](#security--governance)
- [Learning Resources](#learning-resources)
- [Contributing](#contributing)

---

## Official Microsoft MCP Servers

First-party servers published by Microsoft product teams.

- **[microsoft/mcp](https://github.com/microsoft/mcp)** — The official catalog of Microsoft MCP server implementations. Includes `Azure.Mcp.Server`, `Fabric.Mcp.Server`, and a `Template.Mcp.Server` scaffold.
- **[Azure/azure-mcp](https://github.com/Azure/azure-mcp)** — The Azure MCP Server. Exposes **230+ tools** across **45+ Azure services** via a single MCP endpoint. Ships built-in with Visual Studio 2026.
- **[microsoft/azure-devops-mcp](https://github.com/microsoft/azure-devops-mcp)** — Azure DevOps MCP Server: repos, pipelines, work items, delivery metadata.
- **[microsoft/fabric-rti-mcp](https://github.com/microsoft/fabric-rti-mcp)** — MCP server for **Microsoft Fabric Real-Time Intelligence**, Eventhouse, Azure Data Explorer (KQL), and other RTI services.
- **[microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)** — Browser automation MCP server powered by Playwright. The de-facto standard for letting agents drive a real browser.
- **[microsoft/skills](https://github.com/microsoft/skills)** — Skills, MCP servers, custom agents, and `AGENTS.md` files for grounding coding agents.
- **[microsoft/mcp-azure-security-guide](https://github.com/microsoft/mcp-azure-security-guide)** — Azure implementation guide for the **OWASP MCP Top 10** security risks.

---

## Azure

### Infrastructure & Management

- **[Azure/azure-mcp](https://github.com/Azure/azure-mcp)** — *(official, see above)*
- **[dminkovski/azure-diagram-mcp](https://github.com/dminkovski/azure-diagram-mcp)** — Turn natural-language prompts into Azure architecture diagrams (PNG) via Python Diagrams + Graphviz.
- **[erikhoward/adls-mcp-server](https://github.com/erikhoward/adls-mcp-server)** — Microsoft Azure Data Lake Storage Gen2 MCP server.
- **[dkmaker/mcp-azure-tablestorage](https://github.com/dkmaker/mcp-azure-tablestorage)** — Query Azure Table Storage from an MCP client during local development.
- **[bmoussaud/mcp-azure-apim](https://github.com/bmoussaud/mcp-azure-apim)** — Use **Azure API Management** to expose any existing REST API as an MCP server, or to proxy/govern existing MCP servers.

### FinOps & Pricing

- **[msftnadavbh/AzurePricingMCP](https://github.com/msftnadavbh/AzurePricingMCP)** — Programmatic Azure pricing with FinOps features: Spot analysis, savings, orphaned/underutilized resource detection.
- **[sboludaf/mcp-azure-pricing](https://github.com/sboludaf/mcp-azure-pricing)** — Azure pricing queries over MCP.

### DevOps & CI/CD

- **[microsoft/azure-devops-mcp](https://github.com/microsoft/azure-devops-mcp)** — *(official, see above)*
- **[Vortiago/mcp-azure-devops](https://github.com/Vortiago/mcp-azure-devops)** — Azure DevOps MCP server (Python SDK).
- **[viamus/mcp-azure-devops](https://github.com/viamus/mcp-azure-devops)** — Azure DevOps MCP over HTTP for repos, pipelines, work items, delivery metadata.
- **[renatogroffe/azdevops-apisec-mcp-audit](https://github.com/renatogroffe/azdevops-apisec-mcp-audit)** — APIsec MCP Discovery & Audit from an Azure DevOps pipeline.

### AI Gateway

- **[Azure-Samples/AI-Gateway](https://github.com/Azure-Samples/AI-Gateway)** — Labs that combine **Azure API Management** + Microsoft Foundry + MCP servers to build governed AI gateways.

---

## Microsoft 365 & Graph

- **[acuvity/mcp-server-microsoft-graph](https://github.com/acuvity/mcp-server-microsoft-graph)** — Microsoft Graph MCP server (users, mail, calendar, Teams).
- **[bradystroud/mcp-server-microsoft-graph](https://github.com/bradystroud/mcp-server-microsoft-graph)** — Alternative community implementation of Microsoft Graph via MCP.
- **[godwin3737/mcp-server-microsoft365-filesearch](https://github.com/godwin3737/mcp-server-microsoft365-filesearch)** — Search files across Microsoft 365 via MCP.
- **[michMartineau/mcp-server-microsoft-todo](https://github.com/michMartineau/mcp-server-microsoft-todo)** — Microsoft To-Do MCP server written in Go.

---

## Fabric, Power BI & Data

- **[microsoft/fabric-rti-mcp](https://github.com/microsoft/fabric-rti-mcp)** — *(official, see above)* — Eventhouse / ADX / KQL via MCP.

> Looking for Power BI, Purview or OneLake MCP servers? Open a PR when you find one — this area is still sparse.

---

## Power Platform & Copilot Studio

- **[aschauera/MCPinCopilotStudio](https://github.com/aschauera/MCPinCopilotStudio)** — Demonstrations of MCP server implementations consumed by **Copilot Studio** agents.
- 📘 **[Extend Copilot Studio agents with MCP servers](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agent-extend-action-mcp)** — Official docs on wiring MCP servers into Copilot Studio.

---

## GitHub

- **[github/github-mcp-server](https://github.com/github/github-mcp-server)** — GitHub's **official MCP Server** (Go). Repos, issues, PRs, Actions, and more.
- 📘 **[GitHub Copilot CLI + Azure MCP](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/how-to/github-copilot-cli)** — Quickstart for combining the GitHub Copilot CLI with the Azure MCP Server.

---

## Developer Tools & Microsoft Learn

- **[microsoft.docs.mcp](https://learn.microsoft.com/en-us/training/support/mcp)** *(hosted)* — Hosted MCP endpoint that searches Microsoft Learn documentation. No local install needed.
- **[ppiova/AgentFX-MCP-MicrosoftLearn](https://github.com/ppiova/AgentFX-MCP-MicrosoftLearn)** — Reference integration of **Microsoft Agent Framework (.NET)** with the Microsoft Learn MCP server.
- **[SumanthReddyV/AI-Agent-with-MCP](https://github.com/SumanthReddyV/AI-Agent-with-MCP)** — AI agent that queries Microsoft Learn docs over MCP.

---

## Playwright & Browser Automation

- **[microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)** — *(official)* — Drive a full browser from your agent. Industry-leading ⭐ count.

---

## MCP Clients in Microsoft Products

Where MCP is **consumed** inside Microsoft tooling today:

- **Visual Studio 2022 / 2026** — Azure MCP tools ship built-in. [Learn more](https://learn.microsoft.com/en-us/visualstudio/ide/mcp-servers).
- **VS Code** — GitHub Copilot Chat supports MCP server configuration. [Docs](https://code.visualstudio.com/docs/copilot/chat/mcp-servers).
- **GitHub Copilot CLI** — Native MCP server support for any MCP-compatible tool.
- **Microsoft Copilot Studio** — Add MCP servers as *actions* from a no-code builder. [Docs](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agent-extend-action-mcp).
- **Microsoft Agent Framework** (.NET / Python) — `Microsoft.Agents.AI` + the C# `ModelContextProtocol` SDK / Python `mcp` SDK for connecting agents to any MCP server.

---

## Community servers in this repo

Reference implementations maintained in this repository. Every server ships a multi-arch image on GHCR with SBOM + build provenance. See [`servers/`](./servers/) for the index and conventions.

- 🐳 **[`azure-resource-graph-mcp`](./servers/azure-resource-graph-mcp/)** — Read-only Azure inventory via **Resource Graph + KQL**. Answer natural-language questions about your estate (*"VMs in eastus > 16 GB?"*). Image: `ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/azure-resource-graph-mcp:latest`.
- 🐳 **[`microsoft-learn-search-mcp`](./servers/microsoft-learn-search-mcp/)** — Search Microsoft Learn docs + fetch articles as Markdown. **No auth, zero setup.** Grounds your agent in canonical Microsoft docs. Image: `ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/microsoft-learn-search-mcp:latest`.
- 🐳 **[`azure-openai-deployments-mcp`](./servers/azure-openai-deployments-mcp/)** — FinOps-friendly inventory of your Azure OpenAI **accounts, deployments and region quotas**. Great for *"where is gpt-4o-mini deployed and how much capacity is left?"* Image: `ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/azure-openai-deployments-mcp:latest`.
- 🐳 **[`github-models-mcp`](./servers/github-models-mcp/)** — Bridge any MCP client to the **free-tier GitHub Models** (OpenAI GPT-4.1, Microsoft Phi-4, Meta Llama 3.3, Mistral, Cohere, DeepSeek…). Lets your main agent **delegate, fallback or A/B compare** across models. Image: `ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/github-models-mcp:latest`.
- 🐳 **[`microsoft-foundry-agents-mcp`](./servers/microsoft-foundry-agents-mcp/)** — Invoke your **Microsoft Foundry hosted agents** (v2 Responses API, `azure-ai-projects` 2.x) from any MCP client. Discover, converse and delegate to the specialized domain agents you already built in Foundry. Image: `ghcr.io/ppiova/mcp-servers-microsoft-ecosystem/microsoft-foundry-agents-mcp:latest`.

> 🚧 Roadmap: `copilot-studio-mcp`, `ms-graph-mcp`, `azure-openai-chat-mcp`. PRs welcome.

---

## Starters & Templates

Production-ready templates to bootstrap your own MCP server for Microsoft services:

- **[ppiova/mcp-docker-starter](https://github.com/ppiova/mcp-docker-starter)** — Python **FastMCP** server + **.NET Agent Framework** client, wired via Docker Compose over a private bridge network. Multi-arch GHCR images, SBOM, non-root containers. Ready to fork for your own Microsoft service.
- **[ppiova/ai-agents-compose-stack](https://github.com/ppiova/ai-agents-compose-stack)** — Multi-agent workflow with **OpenTelemetry + Aspire Dashboard** observability in Compose. Great for wrapping an MCP server with production telemetry.
- **[microsoft/mcp `Template.Mcp.Server`](https://github.com/microsoft/mcp/tree/main/servers/Template.Mcp.Server)** — Official .NET scaffold for new MCP servers.
- **[jtucker/mcp-untappd-server-dotnet](https://github.com/jtucker/mcp-untappd-server-dotnet)** — .NET MCP server running as an **Azure Function** (F#). Useful reference pattern for serverless MCP.

---

## Security & Governance

- **[microsoft/mcp-azure-security-guide](https://github.com/microsoft/mcp-azure-security-guide)** — *(official)* — OWASP **MCP Top 10** risks with Azure-specific mitigations.
- **[bmoussaud/mcp-azure-apim](https://github.com/bmoussaud/mcp-azure-apim)** — APIM as an MCP gateway for auth, rate-limit, and audit.
- **[renatogroffe/azdevops-apisec-mcp-audit](https://github.com/renatogroffe/azdevops-apisec-mcp-audit)** — APIsec scanning of MCP endpoints from Azure DevOps pipelines.

---

## Learning Resources

### Official blogs

- [Introducing Microsoft Agent Framework](https://devblogs.microsoft.com/foundry/introducing-microsoft-agent-framework-the-open-source-engine-for-agentic-ai-apps/) — Azure AI Foundry blog.
- [Azure MCP Server now built-in with Visual Studio 2026](https://devblogs.microsoft.com/visualstudio/azure-mcp-server-now-built-in-with-visual-studio-2026-a-new-era-for-agentic-workflows/) — VS team on the MCP experience.
- [Microsoft Fabric MCP Server announcement (2025-10-01)](https://devblogs.microsoft.com/fabric/) — Fabric + MCP integration.

### Talks & videos (community)

- 🎙️ [**Crea tus propios Agentes de IA con Azure AI Foundry**](https://www.youtube.com/watch?v=dklTcCMSLsU) — *Microsoft Reactor, ES*, Pablo Piovano.
- 🎙️ [**Introducción al Agent Framework y agentes individuales**](https://developer.microsoft.com/en-us/reactor/events/26463/) — *Microsoft Reactor, ES*, Pablo Piovano.
- 🎙️ [**Integración de MCP con LLMs**](https://reactor.microsoft.com/es-es/reactor/events/26167/) — Microsoft Reactor, ES*, Pablo Piovano.

### Articles
- 📝 [LinkedIn Articles](https://www.linkedin.com/in/ppiova/recent-activity/articles/) — LinkedIn.
- 📝 [DEV.TO](https://dev.to/ppiova) — dev.to.

### Books

- 📘 [**AI-102 Certification Guide**](https://a.co/d/0hJv775S) — Practical guide covering Azure AI, GenAI, and Microsoft Foundry (includes agents + MCP).

---

## Contributing

Missing a server? Found a broken link? PRs are very welcome — see **[CONTRIBUTING.md](./CONTRIBUTING.md)** for the required entry format and review checklist.

Quick rules:

1. The server must be **public**, **runnable**, and integrate with a **Microsoft product or service**.
2. One entry per line: `- **[owner/repo](url)** — one-sentence description.`
3. Prefer **Docker-ready** projects; tag with 🐳 if they ship a `Dockerfile` / `compose.yaml`.
4. No paid-only or behind-login resources.

---

## License

[MIT](./LICENSE) — Curated by [Pablo Piovano](https://github.com/ppiova) · Microsoft MVP in AI. Inspired by the [awesome](https://github.com/sindresorhus/awesome) list tradition.
