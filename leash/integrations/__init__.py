"""Integration namespaces — one per provider.

Mirrors ``leash.integrations`` in ``leash-sdk-ts/src/leash.ts``. Strongly
typed namespaces are exposed for the providers the platform proxies with
a stable contract; generic ``IntegrationCaller`` is used for the rest.
"""

from .base import IntegrationCaller, IntegrationsNamespace, _Transport
from .gmail import GmailIntegration
from .google_calendar import GoogleCalendarIntegration
from .google_drive import GoogleDriveIntegration
from .linear import LinearIntegration

__all__ = [
    "IntegrationsNamespace",
    "IntegrationCaller",
    "GmailIntegration",
    "GoogleCalendarIntegration",
    "GoogleDriveIntegration",
    "LinearIntegration",
    "_Transport",
]
