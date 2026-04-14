"""Main LeashIntegrations client."""

import os
from typing import Any, Dict, Optional

import requests

from leash.calendar import CalendarClient
from leash.custom import CustomIntegration
from leash.drive import DriveClient
from leash.gmail import GmailClient
from leash.types import LeashError

DEFAULT_PLATFORM_URL = "https://api.leash.build"


class LeashIntegrations:
    """Client for accessing Leash platform integrations.

    Args:
        auth_token: The leash-auth JWT token (from cookie or env).
        platform_url: Base URL of the Leash platform API.
            Defaults to https://api.leash.build.
        api_key: Optional API key for server-to-server authentication.
    """

    def __init__(
        self,
        auth_token: str,
        platform_url: str = DEFAULT_PLATFORM_URL,
        api_key: Optional[str] = None,
    ):
        self.auth_token = auth_token
        self.platform_url = platform_url.rstrip("/")
        self.api_key = api_key or os.environ.get("LEASH_API_KEY")
        self._env_cache: Optional[Dict[str, str]] = None

    @property
    def gmail(self) -> GmailClient:
        """Gmail integration client."""
        return GmailClient(self._call)

    @property
    def calendar(self) -> CalendarClient:
        """Google Calendar integration client."""
        return CalendarClient(self._call)

    @property
    def drive(self) -> DriveClient:
        """Google Drive integration client."""
        return DriveClient(self._call)

    def integration(self, name: str) -> "CustomIntegration":
        """Access a custom integration by name. Returns an untyped client.

        Args:
            name: The custom integration name.

        Returns:
            A CustomIntegration instance with a ``call`` method for proxied requests.
        """
        return CustomIntegration(name, self._call_custom)

    def _call_custom(self, name: str, path: str, method: str = "GET",
                     body: Optional[Dict[str, Any]] = None,
                     headers: Optional[Dict[str, str]] = None) -> Any:
        """Call the custom integration proxy endpoint.

        Args:
            name: The custom integration name.
            path: The endpoint path to forward.
            method: HTTP method (default GET).
            body: Optional request body.
            headers: Optional extra headers to forward.

        Returns:
            The ``data`` field from the platform response.

        Raises:
            LeashError: If the platform returns a non-success response.
        """
        req_headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }
        if self.api_key:
            req_headers["X-API-Key"] = self.api_key

        payload: Dict[str, Any] = {"path": path, "method": method}
        if body is not None:
            payload["body"] = body
        if headers is not None:
            payload["headers"] = headers

        response = requests.post(
            f"{self.platform_url}/api/integrations/custom/{name}",
            json=payload,
            headers=req_headers,
        )
        data = response.json()
        if not data.get("success"):
            raise LeashError(
                message=data.get("error", "Unknown error"),
                code=data.get("code"),
                connect_url=data.get("connectUrl"),
            )
        return data.get("data")

    def _call(self, provider: str, action: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Call the platform proxy.

        Args:
            provider: Integration provider name (e.g. 'gmail').
            action: Action to perform (e.g. 'list-messages').
            params: Optional request body parameters.

        Returns:
            The ``data`` field from the platform response.

        Raises:
            LeashError: If the platform returns a non-success response.
        """
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        response = requests.post(
            f"{self.platform_url}/api/integrations/{provider}/{action}",
            json=params or {},
            headers=headers,
        )
        data = response.json()
        if not data.get("success"):
            raise LeashError(
                message=data.get("error", "Unknown error"),
                code=data.get("code"),
                connect_url=data.get("connectUrl"),
            )
        return data.get("data")

    def is_connected(self, provider_id: str) -> bool:
        """Check if a provider is connected for the current user.

        Args:
            provider_id: The provider identifier (e.g. 'gmail').

        Returns:
            True if the provider is actively connected, False otherwise.
        """
        try:
            connections = self.get_connections()
            conn = next((c for c in connections if c.get("providerId") == provider_id), None)
            return conn is not None and conn.get("status") == "active"
        except Exception:
            return False

    def get_connections(self) -> list:
        """Get connection status for all providers.

        Returns:
            A list of connection status dicts.
        """
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        response = requests.get(
            f"{self.platform_url}/api/integrations/connections",
            headers=headers,
        )
        data = response.json()
        if not data.get("success"):
            raise LeashError(
                message=data.get("error", "Unknown error"),
                code=data.get("code"),
            )
        return data.get("data", [])

    def mcp(self, package: str, tool: str, args: Optional[Dict[str, Any]] = None) -> Any:
        """Call any MCP server tool directly.

        Args:
            package: The npm package name of the MCP server.
            tool: The tool name to invoke.
            args: Optional arguments to pass to the tool.

        Returns:
            The ``data`` field from the platform response.

        Raises:
            LeashError: If the platform returns a non-success response.
        """
        headers = {
            "Content-Type": "application/json",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        payload: Dict[str, Any] = {"package": package, "tool": tool}
        if args is not None:
            payload["args"] = args

        response = requests.post(
            f"{self.platform_url}/api/mcp/run",
            json=payload,
            headers=headers,
        )
        data = response.json()
        if not data.get("success"):
            raise LeashError(
                message=data.get("error", "Unknown error"),
                code=data.get("code"),
                connect_url=data.get("connectUrl"),
            )
        return data.get("data")

    def get_env(self, key: Optional[str] = None) -> Any:
        """Fetch env vars from the platform. Cached after first call.

        Args:
            key: Optional key to look up. If provided, returns just that value
                (or None if not found). If omitted, returns the full dict.

        Returns:
            A dict of all env vars, or a single value if ``key`` is provided.

        Raises:
            LeashError: If the platform returns a non-success response.
        """
        if self._env_cache is None:
            headers: Dict[str, str] = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"

            response = requests.get(
                f"{self.platform_url}/api/apps/env",
                headers=headers,
            )
            data = response.json()
            if not data.get("success"):
                raise LeashError(
                    message=data.get("error", "Unknown error"),
                    code=data.get("code"),
                )
            self._env_cache = data.get("data", {})

        if key is not None:
            return self._env_cache.get(key)
        return self._env_cache

    def get_connect_url(self, provider_id: str, return_url: Optional[str] = None) -> str:
        """Get the URL to connect a provider (for UI buttons).

        Args:
            provider_id: The provider identifier.
            return_url: Optional URL to redirect back to after connecting.

        Returns:
            The full URL to initiate the OAuth connection flow.
        """
        url = f"{self.platform_url}/api/integrations/connect/{provider_id}"
        if return_url:
            from urllib.parse import quote
            url += f"?return_url={quote(return_url)}"
        return url
