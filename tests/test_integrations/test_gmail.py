"""Tests for ``leash.integrations.gmail``."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict

import httpx
import pytest

from leash import Leash, LeashError


def _route(path: str, status: int, body: Any):
    return {("POST", path): (status, body)}


def _build(http_client, *, with_cookie: bool = True, token: str = "") -> Leash:
    cookies = {"leash-auth": token} if with_cookie and token else {}
    req = SimpleNamespace(cookies=cookies, headers={})
    return Leash(request=req, api_key="lsk_live_x", http_client=http_client)


class TestListMessages:
    def test_returns_message_list(self, http_client_factory, token) -> None:
        client, captures = http_client_factory(
            _route(
                "/api/integrations/gmail/list-messages",
                200,
                {
                    "success": True,
                    "data": {
                        "messages": [{"id": "m1", "threadId": "t1"}],
                        "resultSizeEstimate": 1,
                    },
                },
            )
        )
        with _build(client, token=token) as leash:
            result = leash.integrations.gmail.list_messages(max_results=5)

        assert result == {"messages": [{"id": "m1", "threadId": "t1"}], "resultSizeEstimate": 1}
        assert len(captures) == 1
        req = captures[0]
        assert req.method == "POST"
        body = json.loads(req.content.decode())
        assert body == {"maxResults": 5}

    def test_passes_optional_params(self, http_client_factory, token) -> None:
        client, captures = http_client_factory(
            _route(
                "/api/integrations/gmail/list-messages",
                200,
                {"success": True, "data": {"messages": []}},
            )
        )
        with _build(client, token=token) as leash:
            leash.integrations.gmail.list_messages(
                query="from:x", max_results=10, label_ids=["INBOX"], page_token="pt"
            )
        body = json.loads(captures[0].content.decode())
        assert body == {
            "query": "from:x",
            "maxResults": 10,
            "labelIds": ["INBOX"],
            "pageToken": "pt",
        }


class TestSendMessage:
    def test_required_kwargs(self, http_client_factory, token) -> None:
        client, captures = http_client_factory(
            _route(
                "/api/integrations/gmail/send-message",
                200,
                {"success": True, "data": {"id": "sent"}},
            )
        )
        with _build(client, token=token) as leash:
            result = leash.integrations.gmail.send_message(
                to="a@b.c", subject="hi", body="hello"
            )
        assert result == {"id": "sent"}
        sent_body = json.loads(captures[0].content.decode())
        assert sent_body == {"to": "a@b.c", "subject": "hi", "body": "hello"}


class TestErrors:
    def test_401_raises_unauthorized(self, http_client_factory, token) -> None:
        client, _ = http_client_factory(
            _route(
                "/api/integrations/gmail/list-messages",
                401,
                {"error": "Bad cookie"},
            )
        )
        with _build(client, token=token) as leash:
            with pytest.raises(LeashError) as info:
                leash.integrations.gmail.list_messages()
        assert info.value.code == "UNAUTHORIZED"
        assert info.value.status == 401

    def test_402_raises_upgrade_required(self, http_client_factory, token) -> None:
        client, _ = http_client_factory(
            _route(
                "/api/integrations/gmail/list-messages",
                402,
                {"message": "Upgrade to Growth"},
            )
        )
        with _build(client, token=token) as leash:
            with pytest.raises(LeashError) as info:
                leash.integrations.gmail.list_messages()
        assert info.value.code == "UPGRADE_REQUIRED"
        assert "growth" in info.value.message.lower()

    def test_403_raises_not_enabled(self, http_client_factory, token) -> None:
        client, _ = http_client_factory(
            _route(
                "/api/integrations/gmail/list-messages",
                403,
                {"error": "Not allow-listed"},
            )
        )
        with _build(client, token=token) as leash:
            with pytest.raises(LeashError) as info:
                leash.integrations.gmail.list_messages()
        assert info.value.code == "INTEGRATION_NOT_ENABLED"

    def test_500_raises_generic(self, http_client_factory, token) -> None:
        client, _ = http_client_factory(
            _route(
                "/api/integrations/gmail/list-messages",
                500,
                {"error": "boom"},
            )
        )
        with _build(client, token=token) as leash:
            with pytest.raises(LeashError) as info:
                leash.integrations.gmail.list_messages()
        assert info.value.code == "INTEGRATION_ERROR"
        assert info.value.message == "boom"

    def test_success_false_in_body(self, http_client_factory, token) -> None:
        client, _ = http_client_factory(
            _route(
                "/api/integrations/gmail/list-messages",
                200,
                {"success": False, "error": "Provider returned 429", "code": "RATE_LIMITED"},
            )
        )
        with _build(client, token=token) as leash:
            with pytest.raises(LeashError) as info:
                leash.integrations.gmail.list_messages()
        assert info.value.code == "RATE_LIMITED"
        assert "429" in info.value.message
