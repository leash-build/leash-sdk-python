"""Main LeashIntegrations client."""

from typing import Any, Dict, Optional

import requests

from leash.calendar import CalendarClient
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
        self.api_key = api_key

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
