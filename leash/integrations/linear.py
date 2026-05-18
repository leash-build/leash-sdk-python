"""Linear integration — mirrors ``leash.integrations.linear`` in TS.

The TS surface uses underscored action names (``list_issues`` etc.) on the
wire — preserved here. Tolerant of the platform sometimes returning a bare
array vs. ``{ issues, cursor }`` envelope.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, cast

from ..types import (
    LinearComment,
    LinearIssue,
    LinearListIssuesResult,
    LinearPriority,
    LinearProject,
    LinearStateType,
    LinearTeam,
)
from .base import _BaseProvider


class LinearIntegration(_BaseProvider):
    provider = "linear"

    def list_issues(
        self,
        *,
        team_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        state_type: Optional[LinearStateType] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> LinearListIssuesResult:
        params: Dict[str, Any] = {}
        if team_id is not None:
            params["teamId"] = team_id
        if assignee_id is not None:
            params["assigneeId"] = assignee_id
        if state_type is not None:
            params["stateType"] = state_type
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor

        raw = self._call("list_issues", params)
        if isinstance(raw, list):
            return cast(LinearListIssuesResult, {"issues": raw})
        if isinstance(raw, dict):
            out: Dict[str, Any] = {"issues": raw.get("issues", [])}
            if "cursor" in raw and raw["cursor"] is not None:
                out["cursor"] = raw["cursor"]
            return cast(LinearListIssuesResult, out)
        return cast(LinearListIssuesResult, {"issues": []})

    def get_issue(self, id: str) -> LinearIssue:
        return cast(LinearIssue, self._call("get_issue", {"id": id}))

    def create_issue(
        self,
        *,
        team_id: str,
        title: str,
        description: Optional[str] = None,
        assignee_id: Optional[str] = None,
        priority: Optional[LinearPriority] = None,
        label_ids: Optional[List[str]] = None,
    ) -> LinearIssue:
        params: Dict[str, Any] = {"teamId": team_id, "title": title}
        if description is not None:
            params["description"] = description
        if assignee_id is not None:
            params["assigneeId"] = assignee_id
        if priority is not None:
            params["priority"] = priority
        if label_ids is not None:
            params["labelIds"] = label_ids
        return cast(LinearIssue, self._call("create_issue", params))

    def update_issue(
        self,
        id: str,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        assignee_id: Optional[str] = None,
        priority: Optional[LinearPriority] = None,
        label_ids: Optional[List[str]] = None,
        team_id: Optional[str] = None,
    ) -> LinearIssue:
        params: Dict[str, Any] = {"id": id}
        if title is not None:
            params["title"] = title
        if description is not None:
            params["description"] = description
        if assignee_id is not None:
            params["assigneeId"] = assignee_id
        if priority is not None:
            params["priority"] = priority
        if label_ids is not None:
            params["labelIds"] = label_ids
        if team_id is not None:
            params["teamId"] = team_id
        return cast(LinearIssue, self._call("update_issue", params))

    def add_comment(self, issue_id: str, body: str) -> LinearComment:
        return cast(LinearComment, self._call("add_comment", {"issueId": issue_id, "body": body}))

    def list_teams(self) -> List[LinearTeam]:
        raw = self._call("list_teams", {})
        if isinstance(raw, list):
            return cast(List[LinearTeam], raw)
        if isinstance(raw, dict):
            return cast(List[LinearTeam], raw.get("teams", []))
        return []

    def list_projects(self, *, team_id: Optional[str] = None) -> List[LinearProject]:
        params: Dict[str, Any] = {}
        if team_id is not None:
            params["teamId"] = team_id
        raw = self._call("list_projects", params)
        if isinstance(raw, list):
            return cast(List[LinearProject], raw)
        if isinstance(raw, dict):
            return cast(List[LinearProject], raw.get("projects", []))
        return []


__all__ = ["LinearIntegration"]
