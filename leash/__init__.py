"""Leash SDK - access Gmail, Calendar, Drive and more via the Leash platform."""

from leash.auth import LeashAuthError, LeashUser, get_leash_user, is_authenticated
from leash.client import LeashIntegrations
from leash.custom import CustomIntegration
from leash.types import CustomMcpServerConfig, LeashError

__all__ = [
    "LeashIntegrations",
    "CustomIntegration",
    "CustomMcpServerConfig",
    "LeashError",
    "LeashAuthError",
    "LeashUser",
    "get_leash_user",
    "is_authenticated",
]
__version__ = "0.3.1"
