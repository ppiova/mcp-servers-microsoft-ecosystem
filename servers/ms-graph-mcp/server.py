"""
Microsoft Graph MCP Server -- tenant directory & identity insights.

A read-only MCP server focused on the IT-admin / security / compliance
angle of Microsoft Graph: tenant inventory of users, groups, applications,
service principals, group memberships and directory role assignments.

Authenticates via DefaultAzureCredential (azure.identity.aio):
  - AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_CLIENT_SECRET env vars
    (service principal -- recommended for containers and CI)
  - Managed Identity (when deployed to Azure compute)

Required Microsoft Graph application permissions (admin consent):
  - Directory.Read.All        (umbrella -- covers users / groups / apps)
  - RoleManagement.Read.Directory  (for directory role assignments)

Tools:
  get_tenant_overview()                                  -- snapshot counts
  list_users(filter_query?, search?, top=50)             -- directory users
  get_user(upn_or_id)                                    -- profile + manager + licenses
  list_groups(filter_query?, top=50)                     -- groups
  list_group_members(group_id, top=50)                   -- direct members
  list_applications(filter_query?, top=50)               -- registered apps
  list_service_principals(filter_query?, top=50)         -- service principals
  list_directory_role_assignments(top=50)                -- admin role assignments

Exposed on Streamable HTTP transport at /mcp (default port 8000).
"""
from __future__ import annotations

import os
from typing import Any

from azure.identity.aio import DefaultAzureCredential
from kiota_abstractions.base_request_configuration import RequestConfiguration
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from msgraph import GraphServiceClient

# ---- Graph client (one credential + client per server lifecycle) ----
_credential = DefaultAzureCredential()
_client = GraphServiceClient(
    credentials=_credential,
    scopes=["https://graph.microsoft.com/.default"],
)

# Required header when using $count=true on directory resources, plus
# advanced query support ($filter on selected fields, $search, $orderby).
_advanced_headers = {"ConsistencyLevel": "eventual"}

# Cap pagination at one Graph page to keep latency predictable. Bumping
# this above 100 would require following @odata.nextLink which isn't
# worth the extra complexity in v1.
_MAX_TOP = 100


# ---- MCP server ----
_default_hosts = [
    "ms-graph-mcp",
    "ms-graph-mcp:8000",
    "localhost",
    "localhost:8000",
    "127.0.0.1",
    "127.0.0.1:8000",
]
_extra_hosts = [
    h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()
]

mcp = FastMCP(
    name="ms-graph-mcp",
    instructions=(
        "Read-only Microsoft Graph MCP server focused on tenant directory and "
        "identity insights: users, groups, applications, service principals, "
        "memberships and directory role assignments. App-only auth respects "
        "the Graph permissions granted to the application -- nothing more."
    ),
    transport_security=TransportSecuritySettings(
        allowed_hosts=_default_hosts + _extra_hosts,
    ),
)


# ---- Helpers ----------------------------------------------------------

def _clamp_top(top: int | None) -> int:
    if top is None:
        return 50
    return max(1, min(int(top), _MAX_TOP))


def _iso(dt: Any) -> str | None:
    """ISO-format a datetime if present, else None."""
    return dt.isoformat() if dt is not None and hasattr(dt, "isoformat") else None


def _user_dict(u: Any) -> dict[str, Any]:
    return {
        "id": u.id,
        "displayName": u.display_name,
        "userPrincipalName": u.user_principal_name,
        "mail": u.mail,
        "accountEnabled": u.account_enabled,
        "userType": u.user_type,
        "jobTitle": u.job_title,
        "department": u.department,
        "createdDateTime": _iso(u.created_date_time),
    }


def _group_dict(g: Any) -> dict[str, Any]:
    return {
        "id": g.id,
        "displayName": g.display_name,
        "mailEnabled": g.mail_enabled,
        "securityEnabled": g.security_enabled,
        "groupTypes": list(g.group_types or []),
        "mail": g.mail,
        "description": g.description,
        "visibility": g.visibility,
        "createdDateTime": _iso(g.created_date_time),
    }


def _application_dict(a: Any) -> dict[str, Any]:
    return {
        "id": a.id,
        "appId": a.app_id,
        "displayName": a.display_name,
        "publisherDomain": a.publisher_domain,
        "signInAudience": a.sign_in_audience,
        "createdDateTime": _iso(a.created_date_time),
    }


def _service_principal_dict(sp: Any) -> dict[str, Any]:
    return {
        "id": sp.id,
        "appId": sp.app_id,
        "displayName": sp.display_name,
        "servicePrincipalType": sp.service_principal_type,
        "accountEnabled": sp.account_enabled,
        "appRoleAssignmentRequired": sp.app_role_assignment_required,
        "homepage": sp.homepage,
    }


def _directory_object_summary(obj: Any) -> dict[str, Any]:
    """Compact summary for any directoryObject (member, role principal, etc)."""
    odata = getattr(obj, "odata_type", None) or getattr(obj, "additional_data", {}).get("@odata.type")
    return {
        "id": getattr(obj, "id", None),
        "type": odata,
        "displayName": getattr(obj, "display_name", None),
        "userPrincipalName": getattr(obj, "user_principal_name", None),
    }


# ---- Tools ------------------------------------------------------------

@mcp.tool()
async def get_tenant_overview() -> dict[str, Any]:
    """Snapshot counts for the tenant: users, groups, applications, service principals.

    Useful as a first call to understand the size and shape of a tenant before drilling in.
    Each entry is either an integer count or an `<entity>_error` field with the failure reason
    (e.g. when the application is missing the corresponding Graph permission).
    """
    out: dict[str, Any] = {}
    config = RequestConfiguration(headers=_advanced_headers)

    try:
        out["users"] = await _client.users.count.get(request_configuration=config)
    except Exception as e:  # noqa: BLE001 -- surface the message to the caller
        out["users_error"] = str(e)

    try:
        out["groups"] = await _client.groups.count.get(request_configuration=config)
    except Exception as e:  # noqa: BLE001
        out["groups_error"] = str(e)

    try:
        out["applications"] = await _client.applications.count.get(
            request_configuration=config
        )
    except Exception as e:  # noqa: BLE001
        out["applications_error"] = str(e)

    try:
        out["servicePrincipals"] = await _client.service_principals.count.get(
            request_configuration=config
        )
    except Exception as e:  # noqa: BLE001
        out["servicePrincipals_error"] = str(e)

    return out


@mcp.tool()
async def list_users(
    filter_query: str | None = None,
    search: str | None = None,
    top: int = 50,
) -> list[dict[str, Any]]:
    """List directory users (capped at 100 per call, no pagination beyond that).

    Args:
        filter_query: OData $filter, e.g. "accountEnabled eq false" or "userType eq 'Guest'".
        search: OData $search, e.g. '"displayName:Pablo"' (Graph requires the inner quotes).
        top: Page size (max 100).
    """
    from msgraph.generated.users.users_request_builder import UsersRequestBuilder

    qp = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
        top=_clamp_top(top),
        select=[
            "id",
            "displayName",
            "userPrincipalName",
            "mail",
            "accountEnabled",
            "userType",
            "jobTitle",
            "department",
            "createdDateTime",
        ],
    )
    if filter_query:
        qp.filter = filter_query
    if search:
        qp.search = search
    config = RequestConfiguration(query_parameters=qp, headers=_advanced_headers)

    response = await _client.users.get(request_configuration=config)
    if response is None or response.value is None:
        return []
    return [_user_dict(u) for u in response.value]


@mcp.tool()
async def get_user(upn_or_id: str) -> dict[str, Any]:
    """Return a user's profile, manager and assigned licenses.

    Args:
        upn_or_id: User principal name (`alice@contoso.com`) or object ID.
    """
    user = await _client.users.by_user_id(upn_or_id).get()
    if user is None:
        return {"error": "user not found"}

    profile = _user_dict(user)

    # Manager (optional -- not every user has one)
    try:
        mgr = await _client.users.by_user_id(upn_or_id).manager.get()
        profile["manager"] = _directory_object_summary(mgr) if mgr is not None else None
    except Exception as e:  # noqa: BLE001
        profile["manager_error"] = str(e)

    # License assignments (skuId list)
    try:
        details = await _client.users.by_user_id(upn_or_id).license_details.get()
        if details is not None and details.value is not None:
            profile["licenses"] = [
                {"skuId": d.sku_id, "skuPartNumber": d.sku_part_number}
                for d in details.value
            ]
        else:
            profile["licenses"] = []
    except Exception as e:  # noqa: BLE001
        profile["licenses_error"] = str(e)

    return profile


@mcp.tool()
async def list_groups(
    filter_query: str | None = None,
    top: int = 50,
) -> list[dict[str, Any]]:
    """List groups (security + Microsoft 365), capped at 100 per call.

    Args:
        filter_query: OData $filter, e.g. "groupTypes/any(c:c eq 'Unified')" for M365 groups.
        top: Page size (max 100).
    """
    from msgraph.generated.groups.groups_request_builder import GroupsRequestBuilder

    qp = GroupsRequestBuilder.GroupsRequestBuilderGetQueryParameters(
        top=_clamp_top(top),
        select=[
            "id",
            "displayName",
            "mailEnabled",
            "securityEnabled",
            "groupTypes",
            "mail",
            "description",
            "visibility",
            "createdDateTime",
        ],
    )
    if filter_query:
        qp.filter = filter_query
    config = RequestConfiguration(query_parameters=qp, headers=_advanced_headers)

    response = await _client.groups.get(request_configuration=config)
    if response is None or response.value is None:
        return []
    return [_group_dict(g) for g in response.value]


@mcp.tool()
async def list_group_members(group_id: str, top: int = 50) -> list[dict[str, Any]]:
    """List direct members of a group (users, groups, service principals)."""
    from msgraph.generated.groups.item.members.members_request_builder import (
        MembersRequestBuilder,
    )

    qp = MembersRequestBuilder.MembersRequestBuilderGetQueryParameters(top=_clamp_top(top))
    config = RequestConfiguration(query_parameters=qp)
    response = await _client.groups.by_group_id(group_id).members.get(
        request_configuration=config
    )
    if response is None or response.value is None:
        return []
    return [_directory_object_summary(m) for m in response.value]


@mcp.tool()
async def list_applications(
    filter_query: str | None = None,
    top: int = 50,
) -> list[dict[str, Any]]:
    """List app registrations in the tenant.

    Args:
        filter_query: OData $filter, e.g. "signInAudience eq 'AzureADMyOrg'".
        top: Page size (max 100).
    """
    from msgraph.generated.applications.applications_request_builder import (
        ApplicationsRequestBuilder,
    )

    qp = ApplicationsRequestBuilder.ApplicationsRequestBuilderGetQueryParameters(
        top=_clamp_top(top),
        select=[
            "id",
            "appId",
            "displayName",
            "publisherDomain",
            "signInAudience",
            "createdDateTime",
        ],
    )
    if filter_query:
        qp.filter = filter_query
    config = RequestConfiguration(query_parameters=qp, headers=_advanced_headers)

    response = await _client.applications.get(request_configuration=config)
    if response is None or response.value is None:
        return []
    return [_application_dict(a) for a in response.value]


@mcp.tool()
async def list_service_principals(
    filter_query: str | None = None,
    top: int = 50,
) -> list[dict[str, Any]]:
    """List service principals in the tenant (apps + managed identities).

    Args:
        filter_query: OData $filter, e.g. "servicePrincipalType eq 'ManagedIdentity'".
        top: Page size (max 100).
    """
    from msgraph.generated.service_principals.service_principals_request_builder import (
        ServicePrincipalsRequestBuilder,
    )

    qp = ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetQueryParameters(
        top=_clamp_top(top),
        select=[
            "id",
            "appId",
            "displayName",
            "servicePrincipalType",
            "accountEnabled",
            "appRoleAssignmentRequired",
            "homepage",
        ],
    )
    if filter_query:
        qp.filter = filter_query
    config = RequestConfiguration(query_parameters=qp, headers=_advanced_headers)

    response = await _client.service_principals.get(request_configuration=config)
    if response is None or response.value is None:
        return []
    return [_service_principal_dict(sp) for sp in response.value]


@mcp.tool()
async def list_directory_role_assignments(top: int = 50) -> list[dict[str, Any]]:
    """List active directory role assignments (admin roles).

    Returns role display names with the principals they're assigned to. Requires
    `RoleManagement.Read.Directory` application permission.
    """
    from msgraph.generated.role_management.directory.role_assignments.role_assignments_request_builder import (
        RoleAssignmentsRequestBuilder,
    )

    qp = RoleAssignmentsRequestBuilder.RoleAssignmentsRequestBuilderGetQueryParameters(
        top=_clamp_top(top),
        expand=["principal", "roleDefinition"],
    )
    config = RequestConfiguration(query_parameters=qp)
    response = await _client.role_management.directory.role_assignments.get(
        request_configuration=config
    )
    if response is None or response.value is None:
        return []
    out: list[dict[str, Any]] = []
    for a in response.value:
        role_def = getattr(a, "role_definition", None)
        principal = getattr(a, "principal", None)
        out.append({
            "id": a.id,
            "roleDefinition": {
                "id": getattr(role_def, "id", None),
                "displayName": getattr(role_def, "display_name", None),
                "templateId": getattr(role_def, "template_id", None),
            } if role_def is not None else None,
            "principal": _directory_object_summary(principal) if principal is not None else None,
        })
    return out


# ---- Entrypoint -------------------------------------------------------

if __name__ == "__main__":
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))
    mcp.settings.host = host
    mcp.settings.port = port
    print(
        f"[ms-graph-mcp] Streamable HTTP listening on http://{host}:{port}/mcp",
        flush=True,
    )
    mcp.run(transport="streamable-http")
