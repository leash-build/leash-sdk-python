"""Shared HTTP transport + base provider class for integrations.

Mirrors the ``_call`` / ``_post`` private methods on the TS ``Leash``
class. Splitting it out lets each provider module stay focused on its
verbs without duplicating the auth-header / error-mapping logic.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

from ..errors import LeashError

if TYPE_CHECKING:  # pragma: no cover - typing only
    import httpx


class _Transport:
    """Wraps the shared ``httpx.Client`` + auth headers.

    The platform contract for integration calls (matches
    leash-sdk-ts/src/leash.ts lines 586–601):

    * ``X-API-Key`` carries the app key (``LEASH_API_KEY``)
    * ``Cookie: leash-auth=…`` forwards the browser session

    The user JWT extracted from an inbound ``Authorization: Bearer …``
    header is intentionally NOT forwarded — the TS SDK warns that the JWT
    path can cause platform-side ``verifyToken()`` to reject before the
    X-API-Key is checked. Bearer tokens are still accepted by ``Leash``
    for other code paths (e.g. CLI agent flows) but never sent on
    integration POSTs.
    """

    def __init__(
        self,
        *,
        platform_url: str,
        api_key: Optional[str],
        cookie_value: Optional[str],
        http_client: "httpx.Client",
    ) -> None:
        self.platform_url = platform_url
        self.api_key = api_key
        self.cookie_value = cookie_value
        self._http = http_client

    def call(
        self,
        provider: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """POST to ``/api/integrations/{provider}/{action}``."""
        url = f"{self.platform_url}/api/integrations/{provider}/{action}"
        docs_url = f"https://leash.build/docs/integrations/{provider}"
        return self._post(url, params, docs_url=docs_url)

    def _post(
        self,
        url: str,
        params: Optional[Dict[str, Any]],
        *,
        docs_url: str,
    ) -> Any:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if self.cookie_value:
            headers["Cookie"] = f"leash-auth={self.cookie_value}"

        try:
            resp = self._http.post(url, json=params or {}, headers=headers)
        except Exception as exc:
            raise LeashError(
                code="NETWORK_ERROR",
                message=str(exc) or "Failed to reach the Leash platform.",
                action="Check your network connection and that the Leash platform is reachable.",
                see_also="https://leash.build/docs/sdk",
                cause=exc,
            ) from exc

        if resp.status_code >= 400:
            self._raise_for_status(resp, docs_url=docs_url)

        try:
            body: Any = resp.json()
        except Exception as exc:
            raise LeashError(
                code="INTEGRATION_ERROR",
                message="Platform returned an unparseable response.",
                action="Check the Leash platform status and your configuration.",
                see_also=docs_url,
                status=resp.status_code,
                cause=exc,
            ) from exc

        if isinstance(body, dict):
            # Platform contract: { success, data } OR { data } OR raw shape.
            if body.get("success") is False:
                err_val = body.get("error")
                err_msg: str = err_val if isinstance(err_val, str) else "Integration error"
                code_val = body.get("code")
                code: str = code_val if isinstance(code_val, str) else "INTEGRATION_ERROR"
                raise LeashError(
                    code=code,
                    message=err_msg or "Integration error",
                    action="Check your integration configuration and try again.",
                    see_also=docs_url,
                    status=resp.status_code,
                )
            return body.get("data", body)
        return body

    @staticmethod
    def _raise_for_status(resp: "httpx.Response", *, docs_url: str) -> None:
        message = f"HTTP {resp.status_code}"
        body: Any = None
        try:
            body = resp.json()
            if isinstance(body, dict) and isinstance(body.get("error"), str):
                message = body["error"]
        except Exception:
            pass

        status = resp.status_code

        if status == 401:
            raise LeashError(
                code="UNAUTHORIZED",
                message=message,
                action=(
                    "Ensure the leash-auth cookie is present, or open your app from "
                    "the Leash dashboard to get a valid session."
                ),
                see_also="https://leash.build/docs/sdk",
                status=status,
            )

        if status == 402:
            msg_val = body.get("message") if isinstance(body, dict) else None
            msg: str = msg_val if isinstance(msg_val, str) else "This feature requires a higher plan."
            raise LeashError(
                code="UPGRADE_REQUIRED",
                message=msg,
                action="Upgrade your plan at https://leash.build/dashboard/billing.",
                see_also="https://leash.build/pricing",
                status=status,
            )

        if status == 403:
            raise LeashError(
                code="INTEGRATION_NOT_ENABLED",
                message=message,
                action=(
                    "Connect the integration at /dashboard/integrations and make sure "
                    "this app is on the allow-list."
                ),
                see_also="https://leash.build/dashboard/integrations",
                status=status,
            )

        raise LeashError(
            code="INTEGRATION_ERROR",
            message=message,
            action="Check your integration configuration and try again.",
            see_also=docs_url,
            status=status,
        )


# ---------------------------------------------------------------------------
# Provider base
# ---------------------------------------------------------------------------


class _BaseProvider:
    """Internal base class — wraps a :class:`_Transport` with a provider id."""

    provider: str = ""

    def __init__(self, transport: _Transport) -> None:
        self._transport = transport

    def _call(self, action: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._transport.call(self.provider, action, params)


class IntegrationCaller(_BaseProvider):
    """Generic escape hatch — call any provider action without a typed wrapper.

    Returned by ``leash.integrations.provider(name)``. Lets customers use
    integrations the SDK doesn't model with typed helpers yet (GitHub,
    HubSpot, Jira, Slack, Gong, Slite, BigQuery, …).
    """

    def __init__(self, transport: _Transport, name: str) -> None:
        super().__init__(transport)
        self.provider = name

    def call(self, action: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._call(action, params)


# ---------------------------------------------------------------------------
# Integrations namespace
# ---------------------------------------------------------------------------


class IntegrationsNamespace:
    """``leash.integrations`` — strongly typed providers + generic caller."""

    def __init__(self, transport: _Transport) -> None:
        self._transport = transport
        # Local imports to avoid a circular dependency through __init__.
        from .gmail import GmailIntegration
        from .google_calendar import GoogleCalendarIntegration
        from .google_drive import GoogleDriveIntegration
        from .linear import LinearIntegration

        self.gmail = GmailIntegration(transport)
        self.google_calendar = GoogleCalendarIntegration(transport)
        self.google_drive = GoogleDriveIntegration(transport)
        self.linear = LinearIntegration(transport)
        # Aliases matching the TS surface (leash.integrations.calendar, .drive).
        # The long names are canonical (match the platform's provider IDs);
        # these aliases point to the same instances so either name works.
        self.calendar = self.google_calendar
        self.drive = self.google_drive

    # Generic escape hatch for un-typed providers.
    def provider(self, name: str) -> IntegrationCaller:
        """Return an :class:`IntegrationCaller` bound to ``name``."""
        return IntegrationCaller(self._transport, name)


__all__ = [
    "IntegrationCaller",
    "IntegrationsNamespace",
    "_BaseProvider",
    "_Transport",
]
