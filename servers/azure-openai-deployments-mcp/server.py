"""
Azure OpenAI Deployments MCP Server.

Read-only FinOps-friendly view of every Azure OpenAI deployment across
the subscriptions the caller can see. Answers questions like:

    "What GPT-4o deployments do I have and in which regions?"
    "Which deployments still have S0 quota left in eastus?"
    "Show me the RAI policy and capacity of my gpt-4o-mini deployment."

Auth is DefaultAzureCredential — so `az login`, service principal, or
Managed Identity all work. Grant **Reader** on the subscriptions/RGs
you want inspected — no more.

Tools:
  list_subscriptions()
  list_openai_accounts(subscription_id?)
  list_deployments(subscription_id, resource_group, account_name)
  get_deployment(subscription_id, resource_group, account_name, deployment_name)
  list_all_deployments(subscription_id?, location?)
  list_usages(subscription_id, location)

Exposed on Streamable HTTP at /mcp (default port 8000).
"""
from __future__ import annotations

import os
from typing import Any

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.mgmt.subscription import SubscriptionClient
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

_credential = DefaultAzureCredential()
_subs = SubscriptionClient(_credential)

_default_hosts = [
    "azure-openai-deployments-mcp",
    "azure-openai-deployments-mcp:8000",
    "localhost", "localhost:8000",
    "127.0.0.1", "127.0.0.1:8000",
]
_extra_hosts = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]

mcp = FastMCP(
    name="azure-openai-deployments-mcp",
    instructions=(
        "Read-only inventory of Azure OpenAI accounts and their model deployments. "
        "Use `list_all_deployments` as a single call to sweep the whole estate. "
        "Pair with `list_usages` for quota / FinOps questions. RBAC is respected; "
        "grant Reader only."
    ),
    transport_security=TransportSecuritySettings(
        allowed_hosts=_default_hosts + _extra_hosts,
    ),
)


def _cs_client(subscription_id: str) -> CognitiveServicesManagementClient:
    return CognitiveServicesManagementClient(_credential, subscription_id)


def _rg_from_id(resource_id: str) -> str:
    parts = resource_id.split("/")
    try:
        idx = [p.lower() for p in parts].index("resourcegroups")
        return parts[idx + 1]
    except (ValueError, IndexError):
        return ""


def _deployment_to_dict(d: Any) -> dict[str, Any]:
    props = d.properties
    model = getattr(props, "model", None)
    sku = getattr(d, "sku", None)
    call_rate_limit = getattr(props, "call_rate_limit", None)
    return {
        "name": d.name,
        "model": {
            "name": getattr(model, "name", None),
            "version": getattr(model, "version", None),
            "format": getattr(model, "format", None),
            "source": getattr(model, "source", None),
        } if model else None,
        "sku": {
            "name": getattr(sku, "name", None),
            "tier": getattr(sku, "tier", None),
            "capacity": getattr(sku, "capacity", None),
        } if sku else None,
        "provisioning_state": getattr(props, "provisioning_state", None),
        "rai_policy_name": getattr(props, "rai_policy_name", None),
        "version_upgrade_option": getattr(props, "version_upgrade_option", None),
        "call_rate_limit": {
            "count": getattr(call_rate_limit, "count", None),
            "renewal_period": getattr(call_rate_limit, "renewal_period", None),
        } if call_rate_limit else None,
        "capabilities": getattr(props, "capabilities", None),
    }


@mcp.tool()
def list_subscriptions() -> list[dict[str, Any]]:
    """List every Azure subscription the signed-in identity can see."""
    return [
        {
            "id": s.subscription_id,
            "name": s.display_name,
            "state": s.state,
            "tenant_id": s.tenant_id,
        }
        for s in _subs.subscriptions.list()
    ]


@mcp.tool()
def list_openai_accounts(subscription_id: str | None = None) -> list[dict[str, Any]]:
    """List Azure OpenAI accounts (`kind == 'OpenAI'`) across subscriptions.

    Omit `subscription_id` to sweep all accessible subscriptions.
    """
    subs = (
        [subscription_id]
        if subscription_id
        else [s.subscription_id for s in _subs.subscriptions.list() if s.subscription_id]
    )

    out: list[dict[str, Any]] = []
    for sub_id in subs:
        client = _cs_client(sub_id)
        try:
            for acc in client.accounts.list():
                if (acc.kind or "").lower() != "openai":
                    continue
                out.append({
                    "subscription_id": sub_id,
                    "name": acc.name,
                    "resource_group": _rg_from_id(acc.id or ""),
                    "location": acc.location,
                    "kind": acc.kind,
                    "sku": acc.sku.name if acc.sku else None,
                    "endpoint": getattr(acc.properties, "endpoint", None) if acc.properties else None,
                    "id": acc.id,
                })
        except HttpResponseError as e:
            # Skip subs we can't read — don't break the whole listing
            out.append({"subscription_id": sub_id, "error": f"{e.status_code}: {e.reason}"})
    return out


@mcp.tool()
def list_deployments(
    subscription_id: str,
    resource_group: str,
    account_name: str,
) -> list[dict[str, Any]]:
    """List model deployments on a specific Azure OpenAI account."""
    client = _cs_client(subscription_id)
    return [_deployment_to_dict(d) for d in client.deployments.list(resource_group, account_name)]


@mcp.tool()
def get_deployment(
    subscription_id: str,
    resource_group: str,
    account_name: str,
    deployment_name: str,
) -> dict[str, Any]:
    """Get full metadata for a specific deployment — model, SKU, capacity, RAI policy, rate limits."""
    client = _cs_client(subscription_id)
    d = client.deployments.get(resource_group, account_name, deployment_name)
    return _deployment_to_dict(d)


@mcp.tool()
def list_all_deployments(
    subscription_id: str | None = None,
    location: str | None = None,
) -> list[dict[str, Any]]:
    """Flat view of every deployment across every OpenAI account in scope.

    Optionally filter by `location` (Azure region, e.g. 'eastus2').
    Handy for questions like *"where is gpt-4o deployed?"*.
    """
    accounts = list_openai_accounts(subscription_id)
    results: list[dict[str, Any]] = []
    for acc in accounts:
        if "error" in acc:
            continue
        if location and (acc.get("location") or "").lower() != location.lower():
            continue
        sub_id = acc["subscription_id"]
        rg = acc["resource_group"]
        name = acc["name"]
        try:
            for d in list_deployments(sub_id, rg, name):
                d["subscription_id"] = sub_id
                d["resource_group"] = rg
                d["account_name"] = name
                d["account_location"] = acc.get("location")
                d["endpoint"] = acc.get("endpoint")
                results.append(d)
        except HttpResponseError as e:
            results.append({
                "subscription_id": sub_id,
                "resource_group": rg,
                "account_name": name,
                "error": f"{e.status_code}: {e.reason}",
            })
    return results


@mcp.tool()
def list_usages(subscription_id: str, location: str) -> list[dict[str, Any]]:
    """Show Azure OpenAI **quota usage** for a region (tokens/min per SKU & model).

    Great for FinOps and capacity planning — spot which deployments are near their quota.
    """
    client = _cs_client(subscription_id)
    return [
        {
            "name": u.name.value if u.name else None,
            "localized_name": u.name.localized_value if u.name else None,
            "current_value": u.current_value,
            "limit": u.limit,
            "unit": u.unit,
            "quota_period": u.quota_period,
            "status": u.status,
        }
        for u in client.usages.list(location)
    ]


if __name__ == "__main__":
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))
    mcp.settings.host = host
    mcp.settings.port = port
    print(
        f"[azure-openai-deployments-mcp] Streamable HTTP listening on http://{host}:{port}/mcp",
        flush=True,
    )
    mcp.run(transport="streamable-http")
