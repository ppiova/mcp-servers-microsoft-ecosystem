# Contributing

Thank you for helping keep this catalog fresh! The goal is simple: **make it easy for developers and agents to find MCP servers for the Microsoft ecosystem and trust that each entry works.**

## Scope

An entry fits here if **all** of these are true:

1. **It's an MCP server** (implements the [Model Context Protocol](https://modelcontextprotocol.io/)) — *or* it's an MCP client / tool / doc directly relevant to using MCP with Microsoft products.
2. **It integrates with a Microsoft product or service** — Azure, Microsoft 365, Graph, Fabric, Power Platform, Copilot Studio, GitHub, Learn, Visual Studio, VS Code, Windows, etc.
3. **It's public and runnable** — anyone must be able to read the source and stand it up.
4. **It's not paid-only or behind a login wall** — free-tier access is fine, paywalls are not.

## How to add a server

Open a PR that edits `README.md`. Keep the diff small and focused.

### Entry format

```markdown
- **[owner/repo](https://github.com/owner/repo)** — One-sentence description that explains what the server does and which Microsoft service it connects to.
```

Optional markers you can append to the description:

- 🐳 *ships a Dockerfile / `compose.yaml`*
- 🧪 *preview / experimental*
- 🏢 *requires enterprise license or tenant admin*
- 🔒 *requires non-trivial auth setup*

### Placement

Add the entry to the **section** that best matches the Microsoft service. If a server spans multiple areas, place it under the primary one and optionally cross-reference.

Keep each section **alphabetical by repo name** unless there's a clear reason (e.g. "Official" subsections come first).

### Review checklist

Before submitting a PR, verify:

- [ ] Link resolves (not 404, not a dead redirect).
- [ ] Repo has a recent commit (< 12 months) **or** is clearly complete/archived on purpose.
- [ ] Description is under ~150 characters and written in plain English.
- [ ] License is present and permissive (MIT / Apache-2.0 / similar). Note any exceptions in the PR description.
- [ ] Not already listed elsewhere in the catalog.

## How to remove / update an entry

- **Broken / archived / link-rotten** → PR to remove. Keep the commit message short: `remove dead link: owner/repo`.
- **Outdated description** → PR to update. Feel free to re-word for clarity.
- **Moved ownership** → PR to update the URL. Reference the old URL in the PR body for audit.

## Proposing new sections

If you believe a new section is needed (e.g. Windows, Microsoft Teams apps, Dynamics 365), open an issue first with:

1. What the section would cover.
2. At least 3 candidate entries.

If ≥ 3 viable entries exist, we'll add the section.

## Style

- **Tone**: direct, useful, neutral. No marketing language.
- **Formatting**: markdown, no inline HTML unless truly necessary.
- **Emojis**: sparingly — only the tag set above or section headers.
- **Capitalization**: "MCP server" (not "Mcp Server"), "Microsoft Agent Framework" (always full name), "Azure OpenAI", "Microsoft 365".

## Out of scope

We won't list:

- Closed-source tools that happen to "speak MCP" but have no public repo.
- Generic AI resources unrelated to MCP.
- Personal opinions / rants / "best framework" debates (open an issue elsewhere).

## Questions?

Open an issue — or find [Pablo](https://github.com/ppiova) on [LinkedIn](https://www.linkedin.com/in/ppiova/).
