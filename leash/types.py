"""Public types exported by the Leash SDK.

Mirrors ``leash-sdk-ts/src/types.ts`` and the integration-specific shapes
in ``leash-sdk-ts/src/integrations/types.ts`` and
``leash-sdk-ts/src/integrations/providers/linear.ts``. Field names follow
the wire format (camelCase) so JSON parsing is a no-op — pass the dicts
through to consumers unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, TypedDict


# ---------------------------------------------------------------------------
# Core user / JWT types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LeashUser:
    """Authenticated Leash user.

    Mirrors the TS ``LeashUser`` interface. ``picture`` is optional.
    """

    id: str
    email: str
    name: str
    picture: Optional[str] = None


class LeashJWTPayload(TypedDict, total=False):
    """Raw JWT claims the Leash platform sets on the ``leash-auth`` cookie."""

    userId: str
    sub: str
    email: str
    name: str
    username: str
    picture: str
    iat: int
    exp: int


# ---------------------------------------------------------------------------
# Gmail shapes (mirror leash-sdk-ts/src/integrations/types.ts)
# ---------------------------------------------------------------------------


class GmailMessage(TypedDict):
    id: str
    threadId: str


class GmailMessageList(TypedDict, total=False):
    messages: List[GmailMessage]
    nextPageToken: str
    resultSizeEstimate: int


class GmailLabel(TypedDict):
    id: str
    name: str
    type: str


class GmailLabelList(TypedDict):
    labels: List[GmailLabel]


# ---------------------------------------------------------------------------
# Google Drive shapes
# ---------------------------------------------------------------------------


class DriveFile(TypedDict, total=False):
    id: str
    name: str
    mimeType: str
    size: str
    createdTime: str
    modifiedTime: str
    parents: List[str]
    webViewLink: str
    webContentLink: str


class DriveFileList(TypedDict, total=False):
    files: List[DriveFile]
    nextPageToken: str


# ---------------------------------------------------------------------------
# Google Calendar shapes
# ---------------------------------------------------------------------------


class CalendarListEntry(TypedDict, total=False):
    id: str
    summary: str
    description: str
    timeZone: str
    primary: bool
    backgroundColor: str
    foregroundColor: str


class CalendarList(TypedDict):
    calendars: List[CalendarListEntry]


class _CalendarTime(TypedDict, total=False):
    dateTime: str
    date: str
    timeZone: str


class _CalendarAttendee(TypedDict, total=False):
    email: str
    responseStatus: str


class CalendarEvent(TypedDict, total=False):
    id: str
    summary: str
    description: str
    location: str
    start: _CalendarTime
    end: _CalendarTime
    attendees: List[_CalendarAttendee]
    status: str
    htmlLink: str
    created: str
    updated: str


class CalendarEventList(TypedDict, total=False):
    events: List[CalendarEvent]
    nextPageToken: str


# ---------------------------------------------------------------------------
# Linear shapes (mirror integrations/providers/linear.ts)
# ---------------------------------------------------------------------------


LinearStateType = Literal[
    "backlog", "unstarted", "started", "completed", "canceled", "triage"
]
LinearPriority = Literal[0, 1, 2, 3, 4]
LinearProjectState = Literal[
    "planned", "started", "paused", "completed", "canceled", "backlog"
]


class LinearUserRef(TypedDict, total=False):
    id: str
    name: str
    email: str
    displayName: str


class LinearStateRef(TypedDict, total=False):
    id: str
    name: str
    type: LinearStateType
    color: str


class LinearTeamRef(TypedDict, total=False):
    id: str
    key: str
    name: str


class LinearIssue(TypedDict, total=False):
    id: str
    identifier: str
    title: str
    description: str
    priority: LinearPriority
    createdAt: str
    updatedAt: str
    url: str
    assignee: LinearUserRef
    state: LinearStateRef
    team: LinearTeamRef
    labelIds: List[str]
    projectId: str


class LinearComment(TypedDict, total=False):
    id: str
    body: str
    issueId: str
    user: LinearUserRef
    createdAt: str
    updatedAt: str
    url: str


class LinearTeam(TypedDict, total=False):
    id: str
    key: str
    name: str
    description: str
    private: bool
    icon: str
    color: str


class LinearProject(TypedDict, total=False):
    id: str
    name: str
    description: str
    state: LinearProjectState
    targetDate: str
    startDate: str
    url: str
    teamIds: List[str]
    progress: float


class LinearListIssuesResult(TypedDict, total=False):
    issues: List[LinearIssue]
    cursor: str


# ---------------------------------------------------------------------------
# Connection + MCP shapes
# ---------------------------------------------------------------------------


ConnectionState = Literal["active", "expired", "revoked", "error", "not_connected"]


class ConnectionStatus(TypedDict, total=False):
    providerId: str
    providerName: str
    status: ConnectionState
    accountEmail: str
    accountId: str
    connectedAt: str


class CustomMcpServerConfig(TypedDict):
    """Resolved config for a customer-registered MCP server.

    Mirrors the TS ``CustomMcpServerConfig`` interface — feed ``url`` and
    ``headers`` straight into your MCP client; Leash is not on the request
    path.
    """

    slug: str
    displayName: str
    url: str
    headers: Dict[str, str]


__all__ = [
    "LeashUser",
    "LeashJWTPayload",
    "GmailMessage",
    "GmailMessageList",
    "GmailLabel",
    "GmailLabelList",
    "DriveFile",
    "DriveFileList",
    "CalendarListEntry",
    "CalendarList",
    "CalendarEvent",
    "CalendarEventList",
    "LinearStateType",
    "LinearPriority",
    "LinearProjectState",
    "LinearUserRef",
    "LinearStateRef",
    "LinearTeamRef",
    "LinearIssue",
    "LinearComment",
    "LinearTeam",
    "LinearProject",
    "LinearListIssuesResult",
    "ConnectionState",
    "ConnectionStatus",
    "CustomMcpServerConfig",
]
