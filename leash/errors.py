"""Structured error type for the Leash SDK.

Mirrors ``leash-sdk-ts/src/errors.ts``. The ``code`` field is the stable
machine-readable identifier consumers should switch on; ``message`` is the
human-readable line; ``action`` and ``see_also`` are optional remediation
hints. Names mirror the TS ``LeashError`` exactly, only the attribute
casing follows Python convention (``see_also`` instead of ``seeAlso``).
"""

from __future__ import annotations

from typing import Optional

LeashErrorCode = str
"""Open string type. Known codes (mirroring leash-sdk-ts/src/errors.ts):

    - ``NO_API_KEY``
    - ``NO_REQUEST_SERVER_CONSTRUCT``
    - ``BROWSER_MODE_UNSUPPORTED``
    - ``UNAUTHORIZED``
    - ``NO_AUTH_CONTEXT``
    - ``CONNECTION_REQUIRED``
    - ``INTEGRATION_NOT_ENABLED``
    - ``INTEGRATION_ERROR``
    - ``PLAN_BLOCK``
    - ``UPGRADE_REQUIRED``
    - ``NETWORK_ERROR``
    - ``KEY_NOT_DECLARED``
    - ``INVALID_KEY``
    - ``SOURCE_RESYNC_FAILED``
    - ``ENV_FETCH_ERROR``
"""


class LeashError(Exception):
    """Structured error raised by every Leash SDK call site.

    Args:
        code: Stable machine-readable identifier (see ``LeashErrorCode``).
        message: Human-readable description.
        action: Optional remediation hint shown after the message.
        see_also: Optional URL for further reading.
        status: Optional HTTP status code when the error originated from
            the platform.
        cause: Optional underlying exception for chaining.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        action: Optional[str] = None,
        see_also: Optional[str] = None,
        status: Optional[int] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.action = action
        self.see_also = see_also
        self.status = status
        self.cause = cause
        if cause is not None:
            self.__cause__ = cause

    def __str__(self) -> str:
        out = f"x {self.message}"
        if self.action:
            out += f"\n  Fix: {self.action}"
        if self.see_also:
            out += f"\n  See: {self.see_also}"
        return out


__all__ = ["LeashError", "LeashErrorCode"]
