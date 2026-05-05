#!/usr/bin/env python3
"""Validate MCP server links in README.md and discover candidates.

For each GitHub repo URL referenced in README.md the script checks:
  - removed (404)
  - archived
  - renamed / transferred (full_name differs from the URL)
  - stale (no push in STALE_THRESHOLD_DAYS)

It then runs heuristic GitHub searches for new MCP servers in the
Microsoft ecosystem that are not already listed. Discovery candidates
are:
  - filtered against `.discovery-ignore` (intentional rejections)
  - flagged with a Docker-readiness marker when the repo root carries
    a Dockerfile or compose file
  - grouped by suggested README section using keyword heuristics

The report is written to `server-check-report.md` and emitted on stdout.
A `has_findings` output is set in $GITHUB_OUTPUT so the workflow can
decide whether to open an issue.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Force UTF-8 so emoji and non-ASCII text in the report print on every host
# (Windows defaults to cp1252 for stdout). Linux runners are already UTF-8.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

GITHUB_API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
SELF_REPO = "ppiova/mcp-servers-microsoft-ecosystem"
README_PATH = Path("README.md")
REPORT_PATH = Path("server-check-report.md")
IGNORE_PATH = Path(".discovery-ignore")

STALE_THRESHOLD_DAYS = 730  # 2 years
DISCOVERY_TOP_N = 20

DOCKER_MARKERS = {
    "dockerfile",
    "compose.yaml",
    "compose.yml",
    "docker-compose.yaml",
    "docker-compose.yml",
}

# Ordered: more specific sections first. The first rule whose keywords
# match the repo's full name + description wins. The empty-keyword fallback
# at the end maps everything else to "Other".
SECTION_RULES: list[tuple[str, list[str]]] = [
    ("Microsoft 365 & Graph", [
        "microsoft graph", " graph ", "m365", "microsoft 365",
        "outlook", "teams", "to-do", "todo", "exchange",
        "sharepoint", "onedrive",
    ]),
    ("Fabric, Power BI & Data", [
        "fabric", "power bi", "powerbi", "onelake", "purview", "synapse",
    ]),
    ("Power Platform & Copilot Studio", [
        "copilot studio", "power platform", "power apps", "power automate",
        "dataverse",
    ]),
    ("Azure / DevOps & CI/CD", [
        "azure devops", "azdevops", "azure pipelines",
    ]),
    ("Azure / FinOps & Pricing", [
        "finops", "azure pricing", " cost ",
    ]),
    ("Azure / AI Gateway", [
        "api management", "apim", "ai gateway",
    ]),
    ("Azure / Infrastructure & Management", [
        "azure", "aks ", "kubernetes", "data lake", "table storage",
        "resource graph", "openai",
    ]),
    ("Developer Tools & Microsoft Learn", [
        "microsoft learn", "ms docs",
    ]),
    ("Starters & Templates", [
        "template", "starter", "scaffold", "boilerplate",
        "azure functions", "remote-mcp",
    ]),
    ("GitHub", [" github "]),
    ("Other", []),
]

GITHUB_URL_RE = re.compile(
    r"https?://github\.com/([A-Za-z0-9][\w.-]*)/([A-Za-z0-9][\w.-]*?)(?:[/#?].*)?(?=[\s)\"'>]|$)",
    re.IGNORECASE,
)


def gh_request(path: str, params: dict | None = None) -> tuple[int, dict | list | None]:
    url = f"{GITHUB_API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "mcp-servers-microsoft-ecosystem-checker",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return 0, None


def extract_repos(readme: str) -> list[tuple[str, str]]:
    """Return unique (owner, repo) pairs from README, skipping the self repo."""
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for m in GITHUB_URL_RE.finditer(readme):
        owner, repo = m.group(1), m.group(2)
        repo = repo.rstrip(".,")
        if repo.endswith(".git"):
            repo = repo[:-4]
        key = f"{owner.lower()}/{repo.lower()}"
        if key in seen or key == SELF_REPO.lower():
            continue
        seen.add(key)
        out.append((owner, repo))
    return out


def validate(owner: str, repo: str) -> dict:
    status, data = gh_request(f"/repos/{owner}/{repo}")
    if status == 404:
        return {"status": "removed"}
    if status != 200 or not isinstance(data, dict):
        return {"status": "error", "code": status}

    full_name = data.get("full_name", "")
    expected = f"{owner}/{repo}"
    info = {
        "status": "ok",
        "full_name": full_name,
        "archived": bool(data.get("archived")),
        "pushed_at": data.get("pushed_at"),
        "stars": data.get("stargazers_count", 0),
        "url": data.get("html_url"),
    }
    if full_name.lower() != expected.lower():
        info["status"] = "renamed"
    elif data.get("archived"):
        info["status"] = "archived"
    elif data.get("pushed_at"):
        pushed = datetime.fromisoformat(data["pushed_at"].replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - pushed).days > STALE_THRESHOLD_DAYS:
            info["status"] = "stale"
    return info


def load_ignore() -> set[str]:
    """Read `.discovery-ignore`. One `owner/repo` per line, `#` for comments."""
    if not IGNORE_PATH.exists():
        return set()
    out: set[str] = set()
    for line in IGNORE_PATH.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line.lower())
    return out


def detect_docker(owner: str, repo: str) -> bool:
    """Return True if the repo root carries a Dockerfile or compose file."""
    status, data = gh_request(f"/repos/{owner}/{repo}/contents/")
    if status != 200 or not isinstance(data, list):
        return False
    names = {item.get("name", "").lower() for item in data if isinstance(item, dict)}
    return bool(names & DOCKER_MARKERS)


def suggest_section(full_name: str, description: str) -> str:
    """Pick the best-matching README section for a candidate repo."""
    text = f" {full_name.lower()} {description.lower()} "
    for section, keywords in SECTION_RULES:
        if not keywords:
            return section
        if any(kw in text for kw in keywords):
            return section
    return "Other"


def discover(known: set[str], ignore: set[str]) -> list[dict]:
    """Search GitHub for MCP servers tied to Microsoft services.

    Skips repos already listed in README (`known`) or explicitly rejected
    in `.discovery-ignore` (`ignore`). Top results are enriched with a
    Docker-readiness flag and a suggested README section.
    """
    candidates: dict[str, dict] = {}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
    queries = [
        f"mcp in:name,description azure stars:>=50 pushed:>{cutoff}",
        f"mcp in:name,description fabric stars:>=20 pushed:>{cutoff}",
        f'mcp in:name,description "microsoft graph" stars:>=20 pushed:>{cutoff}',
        f'mcp in:name,description "copilot studio" stars:>=10 pushed:>{cutoff}',
        f'mcp in:name,description "power platform" stars:>=10 pushed:>{cutoff}',
        f"topic:mcp-server azure stars:>=10 pushed:>{cutoff}",
        f"topic:mcp-server microsoft stars:>=10 pushed:>{cutoff}",
    ]
    for q in queries:
        status, data = gh_request(
            "/search/repositories",
            {"q": q, "sort": "stars", "order": "desc", "per_page": 30},
        )
        if status != 200 or not isinstance(data, dict):
            continue
        for item in data.get("items", []):
            full = item["full_name"].lower()
            if full == SELF_REPO.lower() or full in known or full in ignore:
                continue
            # Skip archived repos: there's no value in surfacing dead code.
            if item.get("archived"):
                continue
            existing = candidates.get(full)
            if not existing or item["stargazers_count"] > existing["stars"]:
                candidates[full] = {
                    "full_name": item["full_name"],
                    "url": item["html_url"],
                    "description": item.get("description") or "",
                    "stars": item["stargazers_count"],
                    "pushed_at": item.get("pushed_at"),
                }
    top = sorted(candidates.values(), key=lambda x: x["stars"], reverse=True)[:DISCOVERY_TOP_N]
    for c in top:
        owner, repo = c["full_name"].split("/", 1)
        c["has_docker"] = detect_docker(owner, repo)
        c["section"] = suggest_section(c["full_name"], c["description"])
    return top


def main() -> int:
    readme = README_PATH.read_text(encoding="utf-8")
    repos = extract_repos(readme)
    print(f"Validating {len(repos)} GitHub repos from README.md...", file=sys.stderr)

    removed: list[dict] = []
    renamed: list[dict] = []
    archived: list[dict] = []
    stale: list[dict] = []
    errors: list[dict] = []
    known: set[str] = set()

    for owner, repo in repos:
        known.add(f"{owner.lower()}/{repo.lower()}")
        info = validate(owner, repo)
        info["original"] = f"{owner}/{repo}"
        bucket = {
            "removed": removed,
            "renamed": renamed,
            "archived": archived,
            "stale": stale,
            "error": errors,
        }.get(info["status"])
        if bucket is not None:
            bucket.append(info)

    ignore = load_ignore()
    candidates = discover(known, ignore)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"_Generated by `check-servers.yml` on {today}._",
        "",
        f"Validated **{len(repos)}** GitHub repos referenced in `README.md`. "
        f"Discovery ignore-list: **{len(ignore)}** entries.",
        "",
    ]
    if removed:
        lines.append("## Removed or 404 — consider delisting")
        for r in removed:
            lines.append(
                f"- [`{r['original']}`](https://github.com/{r['original']}) — repository not found"
            )
        lines.append("")
    if archived:
        lines.append("## Archived — consider delisting or marking deprecated")
        for r in archived:
            lines.append(f"- [`{r['original']}`]({r['url']}) — archived")
        lines.append("")
    if renamed:
        lines.append("## Renamed or transferred — update the URL")
        for r in renamed:
            lines.append(
                f"- [`{r['original']}`](https://github.com/{r['original']}) "
                f"-> [`{r['full_name']}`]({r['url']})"
            )
        lines.append("")
    if stale:
        years = STALE_THRESHOLD_DAYS // 365
        lines.append(f"## Stale — no push in {years}+ years")
        for r in stale:
            pushed = (r.get("pushed_at") or "")[:10]
            lines.append(f"- [`{r['original']}`]({r['url']}) — last push `{pushed}`")
        lines.append("")
    if errors:
        lines.append("## API errors — could not validate")
        for r in errors:
            lines.append(f"- `{r['original']}` — HTTP `{r.get('code')}`")
        lines.append("")
    if candidates:
        lines.append(
            f"## Discovery candidates — top {len(candidates)} by stars (not in README)"
        )
        lines.append("")
        lines.append(
            "> Heuristic search across `topic:mcp-server` and Microsoft-service keywords. "
            "Review each before adding; some may be unrelated. "
            "To suppress a repo from future runs, add it to `.discovery-ignore`."
        )
        lines.append("")
        lines.append(
            "Legend: 🐳 = repo root carries a Dockerfile or compose file."
        )
        lines.append("")

        grouped: dict[str, list[dict]] = defaultdict(list)
        for c in candidates:
            grouped[c.get("section", "Other")].append(c)
        # Render sections in the order defined by SECTION_RULES, then any
        # leftover ("Other" or unknown) at the end.
        section_order = [name for name, _ in SECTION_RULES]
        for section in section_order:
            items = grouped.get(section)
            if not items:
                continue
            lines.append(f"### {section}")
            for c in items:
                docker = "🐳 " if c.get("has_docker") else ""
                desc = (c["description"] or "")[:140].replace("\n", " ").strip()
                lines.append(
                    f"- {docker}[`{c['full_name']}`]({c['url']}) — stars: {c['stars']} — {desc}"
                )
            lines.append("")

    has_findings = bool(removed or renamed or archived or stale or candidates)
    if not has_findings and not errors:
        lines.append("All listed repos validated cleanly. No discovery candidates exceeded thresholds.")

    report = "\n".join(lines)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)

    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write(f"has_findings={'true' if has_findings else 'false'}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
