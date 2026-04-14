"""Custom integration escape hatch for untyped provider access."""

from typing import Any, Callable, Dict, Optional


class CustomIntegration:
    """Untyped client for a custom integration.

    Obtained via ``LeashIntegrations.integration(name)``. Proxies requests
    through the Leash platform at ``/api/integrations/custom/{name}``.

    Args:
        name: The custom integration name.
        call_fn: Internal callable that performs the HTTP request.
    """

    def __init__(self, name: str, call_fn: Callable[..., Any]):
        self._name = name
        self._call_fn = call_fn

    def call(
        self,
        path: str,
        method: str = "GET",
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """Invoke the custom integration proxy.

        Args:
            path: The endpoint path to forward (e.g. "/users").
            method: HTTP method (default "GET").
            body: Optional JSON body to forward.
            headers: Optional extra headers to forward.

        Returns:
            The ``data`` field from the platform response.

        Raises:
            LeashError: If the platform returns a non-success response.
        """
        return self._call_fn(self._name, path, method, body, headers)
