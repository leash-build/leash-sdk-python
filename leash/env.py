"""Runtime env-var primitive — fetches from the Leash platform.

Mirrors ``leash.env.get`` / ``leash.env.getMany`` in
``leash-sdk-ts/src/leash.ts``. Values are cached per-instance for 60 s.
The cache key is the env-var name; the cache is shared between
``get`` and ``get_many``.

Behaviour adapted for Python idiom:

* Returns ``Optional[str]``. ``None`` is used when the platform reports
  the key isn't declared / not found (HTTP 404), so callers can branch
  with a clean ``if value is None`` instead of catching exceptions.
* All other failures (auth, invalid key, plan block, source resync) raise
  :class:`LeashError` with the same ``code`` strings the TS SDK uses.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from urllib.parse import quote

from .errors import LeashError

if TYPE_CHECKING:  # pragma: no cover - typing only
    import httpx

ENV_CACHE_TTL_S = 60.0


@dataclass
class _CacheEntry:
    value: Optional[str]
    expires_at: float


class EnvNamespace:
    """``leash.env`` — runtime env-var fetcher with TTL cache."""

    def __init__(self, platform_url: str, api_key: Optional[str], http_client: "httpx.Client") -> None:
        self._platform_url = platform_url
        self._api_key = api_key
        self._http = http_client
        self._cache: Dict[str, _CacheEntry] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, *, fresh: bool = False) -> Optional[str]:
        """Resolve a single env-var value.

        Args:
            key: The env-var name (uppercase by convention).
            fresh: Skip the TTL cache for this call. The freshly-fetched
                value is still written back to the cache.

        Returns:
            The string value, or ``None`` when the platform reports the
            key as not declared / not found.

        Raises:
            LeashError: For auth, invalid-key, plan, or platform errors.
        """
        now = time.monotonic()
        if not fresh:
            cached = self._cache.get(key)
            if cached and cached.expires_at > now:
                return cached.value

        value = self._fetch(key)
        self._cache[key] = _CacheEntry(value=value, expires_at=now + ENV_CACHE_TTL_S)
        return value

    def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Bulk variant — resolves multiple keys sequentially.

        Each key uses the shared TTL cache.
        """
        return {key: self.get(key) for key in keys}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _fetch(self, key: str) -> Optional[str]:
        if not self._api_key:
            raise LeashError(
                code="NO_API_KEY",
                message="LEASH_API_KEY is required to call leash.env.get().",
                action="Set LEASH_API_KEY in your environment or pass api_key=... to Leash().",
                see_also="https://leash.build/dashboard/organization",
            )

        url = f"{self._platform_url}/api/apps/me/secrets/{quote(key, safe='')}"
        try:
            resp = self._http.get(
                url,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        except Exception as exc:
            raise LeashError(
                code="NETWORK_ERROR",
                message=str(exc) or "Failed to reach the Leash platform.",
                action="Check your network connection and that the Leash platform is reachable.",
                see_also="https://leash.build/docs/sdk",
                cause=exc,
            ) from exc

        if resp.status_code == 400:
            raise LeashError(
                code="INVALID_KEY",
                message=f"Invalid env-var key: '{key}'.",
                action=(
                    "Env-var names must match /^[A-Za-z_][A-Za-z0-9_]*$/ and be no "
                    "longer than 100 characters."
                ),
                see_also="https://leash.build/docs/sdk",
                status=400,
            )

        if resp.status_code == 401:
            raise LeashError(
                code="UNAUTHORIZED",
                message="Missing or invalid LEASH_API_KEY.",
                action="Mint a fresh API key at /dashboard/organization.",
                see_also="https://leash.build/dashboard/organization",
                status=401,
            )

        if resp.status_code == 402:
            required_plan = _maybe_field(resp, "requiredPlan")
            suffix = f" (requiredPlan: {required_plan})" if required_plan else ""
            raise LeashError(
                code="UPGRADE_REQUIRED",
                message=f"leash.env.get requires the Growth plan or above{suffix}.",
                action="Upgrade at https://leash.build/dashboard/billing.",
                see_also="https://leash.build/dashboard/billing",
                status=402,
            )

        if resp.status_code == 404:
            # Adapted behaviour: return None instead of raising so Python
            # callers can branch on missing keys naturally.
            return None

        if resp.status_code == 502:
            platform_error = _maybe_field(resp, "error")
            raise LeashError(
                code="SOURCE_RESYNC_FAILED",
                message=platform_error or "Secret source resync failed on the platform side.",
                action="Check your secret source configuration in the Leash dashboard.",
                see_also="https://leash.build/dashboard",
                status=502,
            )

        if resp.status_code >= 400:
            raise LeashError(
                code="ENV_FETCH_ERROR",
                message=f"Unexpected response from platform: HTTP {resp.status_code}",
                action="Check the Leash platform status and your configuration.",
                see_also="https://leash.build/docs/sdk",
                status=resp.status_code,
            )

        try:
            body: Any = resp.json()
        except Exception as exc:
            raise LeashError(
                code="ENV_FETCH_ERROR",
                message=f"Platform returned an unparseable response for key '{key}'.",
                action="Check the Leash platform status and your configuration.",
                see_also="https://leash.build/docs/sdk",
                status=resp.status_code,
                cause=exc,
            ) from exc

        value = body.get("value") if isinstance(body, dict) else None
        if not isinstance(value, str):
            raise LeashError(
                code="ENV_FETCH_ERROR",
                message=f"Platform returned an unexpected response shape for key '{key}'.",
                action="Check the Leash platform status and your configuration.",
                see_also="https://leash.build/docs/sdk",
                status=resp.status_code,
            )
        return value


def _maybe_field(resp: "httpx.Response", name: str) -> Optional[str]:
    try:
        body = resp.json()
    except Exception:
        return None
    if isinstance(body, dict):
        val = body.get(name)
        if isinstance(val, str):
            return val
    return None


__all__ = ["EnvNamespace", "ENV_CACHE_TTL_S"]
