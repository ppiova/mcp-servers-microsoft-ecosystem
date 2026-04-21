"""
Azure Resource Graph MCP Server.

Read-only inventory of your Azure estate exposed over MCP.
Authenticates via DefaultAzureCredential — works with:
  - Azure CLI (az login)          ← local dev / devcontainer
  - Service principal env vars    ← CI or container workloads
  - Managed Identity              ← Azure-hosted compute

Tools:
  list_subscriptions()                      — all subs the caller can see
  query_resources(query, subscriptions?)     — run any KQL Resource Graph query
  list_resource_groups(subscription_id)      — RGs in a sub
  list_vms(subscription?, location?)         — convenience: VMs w/ size + location
  list_resources_by_type(type, subscription?) — convenience: all resources of a type

Exposed on Streamable HTTP transport at /mcp (default port 8000).
"""
from __future__ import annotations

import os
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest, QueryRequestOptions
from azure.mgmt.subscription import SubscriptionClient
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# ---- Azure clients (one credential shared across the server lifecycle) ----
_credential = DefaultAzureCredential()
_graph = ResourceGraphClient(_credential)
_subs = SubscriptionClient(_credential)

# ---- MCP server ----
_default_hosts = [
    "azure-resource-graph-mcp",
    "azure-resource-graph-mcp:8000",
    "localhost", "localhost:8000",
    "127.0.0.1", "127.0.0.1:8000",
]
_extra_hosts = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]

mcp = FastMCP(
    name="azure-resource-graph-mcp",
    instructions=(
        "Read-only inventory of the caller's Azure estate via Azure Resource Graph. "
        "Prefer `query_resources` with a KQL query for power users. Use the convenience "
        "tools (`list_vms`, `list_resources_by_type`) for simple common cases. "
        "All operations respect RBAC — you only see what the signed-in identity can see."
    ),
    transport_security=TransportSecuritySettings(
        allowed_hosts=_default_hosts + _extra_hosts,
    ),
)


def _run_query(query: str, subscriptions: list[str] | None, top: int) -> dict[str, Any]:
    options = QueryRequestOptions(top=top)
    request = QueryRequest(subscriptions=subscriptions, query=query, options=options)
    response = _graph.resources(request)
    return {
        "count": response.count,
        "total_records": response.total_records,
        "result_truncated": response.result_truncated,
        "data": response.data,
    }


@mcp.tool()
def list_subscriptions() -> list[dict[str, Any]]:
    """List all Azure subscriptions the caller has access to."""
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
def query_resources(
    query: str,
    subscription_ids: list[str] | None = None,
    top: int = 100,
) -> dict[str, Any]:
    """Run a KQL query against Azure Resource Graph.

    Args:
        query: KQL query string. Examples:
            - "Resources | where type =~ 'Microsoft.Compute/virtualMachines'
               | project name, location, properties.hardwareProfile.vmSize"
            - "ResourceContainers | where type == 'microsoft.resources/subscriptions/resourcegroups'
               | summarize count() by location"
            - "Resources | where tags.env == 'prod' | project name, type, tags"
        subscription_ids: Restrict the query to these subscriptions. Omit to search all accessible.
        top: Max rows to return (Resource Graph max is 1000).

    Returns:
        dict with `count`, `total_records`, `result_truncated`, and `data` (list of rows).
    """
    return _run_query(query, subscription_ids, top)


@mcp.tool()
def list_resource_groups(subscription_id: str) -> list[dict[str, Any]]:
    """List resource groups inside a subscription, with location and tags."""
    query = (
        "ResourceContainers "
        "| where type == 'microsoft.resources/subscriptions/resourcegroups' "
        "| project name, location, tags, resourceGroup=name"
    )
    return _run_query(query, [subscription_id], 1000)["data"]


@mcp.tool()
def list_vms(
    subscription_id: str | None = None,
    location: str | None = None,
) -> list[dict[str, Any]]:
    """List virtual machines, optionally filtered by subscription and/or Azure region.

    Returns name, resource group, location, VM size, OS type, and power state where available.
    """
    filters = ["type =~ 'Microsoft.Compute/virtualMachines'"]
    if location:
        filters.append(f"location =~ '{location}'")
    query = (
        "Resources "
        f"| where {' and '.join(filters)} "
        "| project name, resourceGroup, location, subscriptionId, "
        "vmSize=properties.hardwareProfile.vmSize, "
        "osType=properties.storageProfile.osDisk.osType, "
        "powerState=properties.extended.instanceView.powerState.displayStatus"
    )
    subs = [subscription_id] if subscription_id else None
    return _run_query(query, subs, 1000)["data"]


@mcp.tool()
def list_resources_by_type(
    resource_type: str,
    subscription_id: str | None = None,
) -> list[dict[str, Any]]:
    """List all resources of a given ARM type (e.g. 'Microsoft.Storage/storageAccounts').

    Use `list_distinct_types` first if unsure what types exist in the estate.
    """
    query = (
        "Resources "
        f"| where type =~ '{resource_type}' "
        "| project name, type, location, resourceGroup, subscriptionId, tags"
    )
    subs = [subscription_id] if subscription_id else None
    return _run_query(query, subs, 1000)["data"]


@mcp.tool()
def list_distinct_types(subscription_id: str | None = None) -> list[dict[str, Any]]:
    """Summarize the distinct ARM resource types present in the estate, with counts.

    Great first call when exploring an unfamiliar subscription.
    """
    query = "Resources | summarize count=count() by type | order by count desc"
    subs = [subscription_id] if subscription_id else None
    return _run_query(query, subs, 1000)["data"]


if __name__ == "__main__":
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))
    mcp.settings.host = host
    mcp.settings.port = port
    print(
        f"[azure-resource-graph-mcp] Streamable HTTP listening on http://{host}:{port}/mcp",
        flush=True,
    )
    mcp.run(transport="streamable-http")
