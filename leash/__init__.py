"""Leash SDK for Python — 0.4 unified client.

Public surface:

    from leash import Leash, LeashError, LeashUser

    leash = Leash(request=request)
    user = leash.auth.user()
    key = leash.env.get("OPENAI_API_KEY")
    msgs = leash.integrations.gmail.list_messages(max_results=5)

See ``leash-sdk-ts/src/leash.ts`` for the canonical surface — this package
mirrors that shape, with Python-idiom adaptations (snake_case verbs, kwargs
for options, ``Optional[str]`` returns instead of throwing on missing env
keys).
"""

from .auth import get_leash_user, is_authenticated
from .client import Leash
from .errors import LeashError, LeashErrorCode
from .integrations.base import IntegrationCaller
from .types import (
    CalendarEvent,
    CalendarEventList,
    CalendarList,
    CalendarListEntry,
    ConnectionStatus,
    CustomMcpServerConfig,
    DriveFile,
    DriveFileList,
    GmailLabel,
    GmailLabelList,
    GmailMessage,
    GmailMessageList,
    LeashJWTPayload,
    LeashUser,
    LinearComment,
    LinearIssue,
    LinearListIssuesResult,
    LinearProject,
    LinearStateType,
    LinearTeam,
)

__all__ = [
    "Leash",
    "LeashError",
    "LeashErrorCode",
    "LeashUser",
    "LeashJWTPayload",
    "IntegrationCaller",
    "get_leash_user",
    "is_authenticated",
    # Type shapes
    "GmailMessage",
    "GmailMessageList",
    "GmailLabel",
    "GmailLabelList",
    "DriveFile",
    "DriveFileList",
    "CalendarList",
    "CalendarListEntry",
    "CalendarEvent",
    "CalendarEventList",
    "LinearIssue",
    "LinearComment",
    "LinearTeam",
    "LinearProject",
    "LinearListIssuesResult",
    "LinearStateType",
    "ConnectionStatus",
    "CustomMcpServerConfig",
]
__version__ = "0.4.0"
