"""Shared types for the Leash SDK."""

from typing import Any, Callable, Dict, Optional, TypedDict


class LeashError(Exception):
    """Raised when a Leash platform API call fails."""

    def __init__(self, message: str, code: Optional[str] = None, connect_url: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.connect_url = connect_url


# Type alias for the internal call function passed to provider clients.
CallFn = Callable[[str, str, Optional[Dict[str, Any]]], Any]


class CustomMcpServerConfig(TypedDict):
    """Resolved config for a customer-registered MCP server (LEA-143).

    Returned by ``LeashIntegrations.get_custom_mcp_config(slug)``. Keys mirror
    the platform JSON shape — feed ``url`` + ``headers`` straight into your
    MCP client.
    """

    slug: str
    displayName: str
    url: str
    headers: Dict[str, str]
