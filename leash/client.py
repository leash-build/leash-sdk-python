"""Unified :class:`Leash` client — Python mirror of ``leash-sdk-ts/src/leash.ts``.

Construction is server-only in 0.4 and requires a request object:

    >>> from leash import Leash
    >>> leash = Leash(request=request)        # Flask, FastAPI, Django, etc.
    >>> user = leash.auth.user()              # Optional[LeashUser]
    >>> key = leash.env.get("OPENAI_API_KEY") # Optional[str]
    >>> msgs = leash.integrations.gmail.list_messages(max_results=5)

Authentication precedence (matches the TS surface):

    1. ``LEASH_API_KEY`` env var (server-only, never request-bound)
    2. ``Authorization: Bearer <jwt>`` header on the request (CLI / agent)
    3. ``leash-auth`` cookie on the request (browser → deployed app)

The constructor inspects the request and stores whichever credentials it
finds; each downstream call attaches them in the correct headers.
"""

from __future__ import annotations

import os
from typing import Any, Optional, TYPE_CHECKING

from .auth import (
    decode_token,
    extract_bearer_token,
    extract_cookie,
    payload_to_user,
)
from .env import EnvNamespace
from .errors import LeashError
from .integrations.base import IntegrationsNamespace, _Transport
from .types import LeashUser

if TYPE_CHECKING:  # pragma: no cover - typing only
    import httpx


DEFAULT_PLATFORM_URL = "https://leash.build"
DEFAULT_TIMEOUT_S = 30.0


class _AuthNamespace:
    """``leash.auth`` — read identity off the request."""

    def __init__(self, request: Any, cookie_value: Optional[str]) -> None:
        self._request = request
        self._cookie_value = cookie_value

    def user(self) -> Optional[LeashUser]:
        """Return the authenticated user, or ``None`` when not authenticated.

        Never raises — swallows decode errors so server handlers can
        branch with a clean ``if user is None``.
        """
        if not self._cookie_value:
            return None
        try:
            payload = decode_token(self._cookie_value)
            return payload_to_user(payload)
        except LeashError:
            return None
        except Exception:
            return None

    def is_authenticated(self) -> bool:
        return self.user() is not None


class Leash:
    """Unified Leash client — namespaces for ``auth``, ``env``, ``integrations``.

    Args:
        request: Any HTTP request object with cookies or headers. Required
            in 0.4 — pass ``request=req`` from your route handler.
        platform_url: Override the platform base URL. Defaults to
            ``LEASH_PLATFORM_URL`` env var or ``https://leash.build``.
        api_key: Explicit ``LEASH_API_KEY`` override. Defaults to env var.
        http_client: Inject a custom ``httpx.Client`` (handy for tests).
            When omitted, an internal client is created and owned by this
            instance.

    Raises:
        LeashError: ``NO_REQUEST_SERVER_CONSTRUCT`` when no request is
            supplied; other codes per the underlying call.
    """

    auth: _AuthNamespace
    env: EnvNamespace
    integrations: IntegrationsNamespace

    def __init__(
        self,
        *,
        request: Any = None,
        platform_url: Optional[str] = None,
        api_key: Optional[str] = None,
        http_client: "Optional[httpx.Client]" = None,
    ) -> None:
        if request is None:
            raise LeashError(
                code="NO_REQUEST_SERVER_CONSTRUCT",
                message="Leash requires a request object in server environments.",
                action="Pass request=req to the Leash constructor in your route handler.",
                see_also="https://leash.build/docs/sdk",
            )

        self._request = request
        self._platform_url = (
            platform_url
            or os.environ.get("LEASH_PLATFORM_URL")
            or DEFAULT_PLATFORM_URL
        ).rstrip("/")

        # Auth precedence: LEASH_API_KEY (env / explicit), bearer header, cookie.
        # All three may coexist — env reads use the API key; integration calls
        # forward all credentials the platform recognises.
        self._api_key = api_key if api_key is not None else os.environ.get("LEASH_API_KEY")
        self._bearer_token = extract_bearer_token(request)
        self._cookie_value = extract_cookie(request)

        self._owns_http_client = http_client is None
        if http_client is None:
            try:
                import httpx
            except ImportError as exc:  # pragma: no cover
                raise LeashError(
                    code="NETWORK_ERROR",
                    message="httpx is required to make HTTP calls.",
                    action="Install with: pip install 'leash-sdk' (httpx is a hard dep).",
                    see_also="https://leash.build/docs/sdk",
                    cause=exc,
                ) from exc
            http_client = httpx.Client(timeout=DEFAULT_TIMEOUT_S)
        self._http = http_client

        # Note: bearer token is intentionally NOT passed to the integrations
        # transport — see _Transport docstring. It's still extracted off the
        # request for other code paths (e.g. future CLI/agent flows).
        self._transport = _Transport(
            platform_url=self._platform_url,
            api_key=self._api_key,
            cookie_value=self._cookie_value,
            http_client=self._http,
        )

        self.auth = _AuthNamespace(request=self._request, cookie_value=self._cookie_value)
        self.env = EnvNamespace(
            platform_url=self._platform_url,
            api_key=self._api_key,
            http_client=self._http,
        )
        self.integrations = IntegrationsNamespace(self._transport)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Release the internal HTTP client when one was created here."""
        if self._owns_http_client and self._http is not None:
            try:
                self._http.close()
            except Exception:
                pass

    def __enter__(self) -> "Leash":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()


__all__ = ["Leash", "DEFAULT_PLATFORM_URL"]
