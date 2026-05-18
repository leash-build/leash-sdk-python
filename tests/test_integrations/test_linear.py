"""Tests for ``leash.integrations.linear``.

Linear is the only typed provider with envelope vs. bare-array tolerance,
so it gets a dedicated test surface.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from leash import Leash


def _build(http_client) -> Leash:
    req = SimpleNamespace(cookies={"leash-auth": ""}, headers={})
    return Leash(request=req, api_key="lsk_live_x", http_client=http_client)


class TestListIssues:
    def test_envelope_shape(self, http_client_factory) -> None:
        client, captures = http_client_factory(
            {
                ("POST", "/api/integrations/linear/list_issues"): (
                    200,
                    {
                        "success": True,
                        "data": {
                            "issues": [{"id": "i1", "title": "Bug"}],
                            "cursor": "next",
                        },
                    },
                )
            }
        )
        with _build(client) as leash:
            result = leash.integrations.linear.list_issues(state_type="started")
        assert result == {
            "issues": [{"id": "i1", "title": "Bug"}],
            "cursor": "next",
        }
        body = json.loads(captures[0].content.decode())
        assert body == {"stateType": "started"}

    def test_bare_array_shape(self, http_client_factory) -> None:
        client, _ = http_client_factory(
            {
                ("POST", "/api/integrations/linear/list_issues"): (
                    200,
                    {"success": True, "data": [{"id": "i1"}]},
                )
            }
        )
        with _build(client) as leash:
            result = leash.integrations.linear.list_issues()
        assert result == {"issues": [{"id": "i1"}]}

    def test_drops_missing_cursor(self, http_client_factory) -> None:
        client, _ = http_client_factory(
            {
                ("POST", "/api/integrations/linear/list_issues"): (
                    200,
                    {"success": True, "data": {"issues": []}},
                )
            }
        )
        with _build(client) as leash:
            assert leash.integrations.linear.list_issues() == {"issues": []}


class TestCreateIssue:
    def test_passes_required_fields(self, http_client_factory) -> None:
        client, captures = http_client_factory(
            {
                ("POST", "/api/integrations/linear/create_issue"): (
                    200,
                    {"success": True, "data": {"id": "new-issue", "title": "Hi"}},
                )
            }
        )
        with _build(client) as leash:
            issue = leash.integrations.linear.create_issue(
                team_id="team-1", title="Hi", priority=2
            )
        assert issue == {"id": "new-issue", "title": "Hi"}
        body = json.loads(captures[0].content.decode())
        assert body == {"teamId": "team-1", "title": "Hi", "priority": 2}


class TestListTeams:
    def test_envelope(self, http_client_factory) -> None:
        client, _ = http_client_factory(
            {
                ("POST", "/api/integrations/linear/list_teams"): (
                    200,
                    {"success": True, "data": {"teams": [{"id": "t1", "key": "LEA", "name": "Leash"}]}},
                )
            }
        )
        with _build(client) as leash:
            teams = leash.integrations.linear.list_teams()
        assert teams == [{"id": "t1", "key": "LEA", "name": "Leash"}]

    def test_bare_array(self, http_client_factory) -> None:
        client, _ = http_client_factory(
            {
                ("POST", "/api/integrations/linear/list_teams"): (
                    200,
                    {"success": True, "data": [{"id": "t1"}]},
                )
            }
        )
        with _build(client) as leash:
            teams = leash.integrations.linear.list_teams()
        assert teams == [{"id": "t1"}]


class TestGenericProviderCaller:
    def test_call_dispatches(self, http_client_factory) -> None:
        client, captures = http_client_factory(
            {
                ("POST", "/api/integrations/slack/post-message"): (
                    200,
                    {"success": True, "data": {"ok": True}},
                )
            }
        )
        with _build(client) as leash:
            slack = leash.integrations.provider("slack")
            result = slack.call("post-message", {"channel": "#general", "text": "hi"})
        assert result == {"ok": True}
        body = json.loads(captures[0].content.decode())
        assert body == {"channel": "#general", "text": "hi"}
