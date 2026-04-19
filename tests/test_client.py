"""Tests for LeashIntegrations client.

Covers:
- Import works without optional deps
- Auth headers sent correctly
- API key from env var
- Error handling (LeashError)
- Env caching
- Provider client wiring (gmail, calendar, drive)
- Connection status
- MCP calls
"""

import os
from unittest.mock import patch, MagicMock
import pytest

from leash import LeashIntegrations, LeashError


def _mock_response(data, success=True, status_code=200):
    """Create a mock requests.Response."""
    resp = MagicMock()
    body = {"success": success}
    if success:
        body["data"] = data
    else:
        body["error"] = data.get("error", "Unknown error")
        body["code"] = data.get("code")
        body["connectUrl"] = data.get("connectUrl")
    resp.json.return_value = body
    resp.status_code = status_code
    return resp


class TestImports:
    """Verify the SDK can be imported cleanly."""

    def test_import_main(self):
        from leash import LeashIntegrations, CustomIntegration, LeashError
        assert LeashIntegrations is not None
        assert CustomIntegration is not None
        assert LeashError is not None

    def test_no_framework_dependency(self):
        """SDK should not import Flask, Django, FastAPI, or any web framework."""
        import leash.client
        import sys
        for mod in ["flask", "django", "fastapi", "starlette"]:
            assert mod not in sys.modules, f"{mod} was imported by the SDK"


class TestClientInit:
    def test_default_platform_url(self):
        client = LeashIntegrations(auth_token="test-token")
        assert client.platform_url == "https://leash.build"

    def test_custom_platform_url(self):
        client = LeashIntegrations(auth_token="test-token", platform_url="https://staging.leash.build/")
        assert client.platform_url == "https://staging.leash.build"  # trailing slash stripped

    def test_api_key_from_constructor(self):
        client = LeashIntegrations(auth_token="test-token", api_key="my-key")
        assert client.api_key == "my-key"

    def test_api_key_from_env(self):
        with patch.dict(os.environ, {"LEASH_API_KEY": "env-key"}):
            client = LeashIntegrations(auth_token="test-token")
            assert client.api_key == "env-key"

    def test_constructor_api_key_overrides_env(self):
        with patch.dict(os.environ, {"LEASH_API_KEY": "env-key"}):
            client = LeashIntegrations(auth_token="test-token", api_key="explicit-key")
            assert client.api_key == "explicit-key"


class TestAuthHeaders:
    @patch("leash.client.requests.post")
    def test_sends_auth_and_api_key_headers(self, mock_post):
        mock_post.return_value = _mock_response({"ok": True})

        client = LeashIntegrations(
            auth_token="jwt-token",
            platform_url="https://test.leash.build",
            api_key="api-key-123",
        )
        client._call("gmail", "list-messages", {"maxResults": 5})

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert headers["Authorization"] == "Bearer jwt-token"
        assert headers["X-API-Key"] == "api-key-123"
        assert headers["Content-Type"] == "application/json"

    @patch("leash.client.requests.post")
    def test_url_construction(self, mock_post):
        mock_post.return_value = _mock_response({"ok": True})

        client = LeashIntegrations(auth_token="t", platform_url="https://test.leash.build")
        client._call("gmail", "list-messages")

        url = mock_post.call_args[0][0]
        assert url == "https://test.leash.build/api/integrations/gmail/list-messages"


class TestProviderClients:
    @patch("leash.client.requests.post")
    def test_gmail_list_messages(self, mock_post):
        mock_post.return_value = _mock_response([{"id": "msg-1"}])

        client = LeashIntegrations(auth_token="t")
        result = client.gmail.list_messages(max_results=5)

        assert result == [{"id": "msg-1"}]
        url = mock_post.call_args[0][0]
        assert "/gmail/list-messages" in url

    @patch("leash.client.requests.post")
    def test_calendar_list_events(self, mock_post):
        mock_post.return_value = _mock_response([{"id": "evt-1"}])

        client = LeashIntegrations(auth_token="t")
        result = client.calendar.list_events()

        assert result == [{"id": "evt-1"}]
        url = mock_post.call_args[0][0]
        assert "/google_calendar/list-events" in url

    @patch("leash.client.requests.post")
    def test_drive_list_files(self, mock_post):
        mock_post.return_value = _mock_response([{"id": "file-1"}])

        client = LeashIntegrations(auth_token="t")
        result = client.drive.list_files()

        assert result == [{"id": "file-1"}]
        url = mock_post.call_args[0][0]
        assert "/google_drive/list-files" in url


class TestErrorHandling:
    @patch("leash.client.requests.post")
    def test_raises_leash_error_on_failure(self, mock_post):
        mock_post.return_value = _mock_response(
            {"error": "Not connected", "code": "not_connected", "connectUrl": "/connect/gmail"},
            success=False,
        )

        client = LeashIntegrations(auth_token="t")

        with pytest.raises(LeashError) as exc_info:
            client._call("gmail", "list-messages")

        assert "Not connected" in str(exc_info.value)
        assert exc_info.value.code == "not_connected"

    @patch("leash.client.requests.post")
    def test_leash_error_has_connect_url(self, mock_post):
        mock_post.return_value = _mock_response(
            {"error": "Not connected", "code": "not_connected", "connectUrl": "/connect/gmail"},
            success=False,
        )

        client = LeashIntegrations(auth_token="t")

        with pytest.raises(LeashError) as exc_info:
            client._call("gmail", "list-messages")

        assert exc_info.value.connect_url == "/connect/gmail"


class TestEnvCache:
    @patch("leash.client.requests.get")
    def test_caches_after_first_call(self, mock_get):
        mock_get.return_value = _mock_response({"DB_URL": "postgres://...", "API_KEY": "abc"})

        client = LeashIntegrations(auth_token="t")

        result1 = client.get_env()
        result2 = client.get_env()
        result3 = client.get_env("DB_URL")

        assert result1 == {"DB_URL": "postgres://...", "API_KEY": "abc"}
        assert result2 == result1
        assert result3 == "postgres://..."
        assert mock_get.call_count == 1  # only one HTTP call

    @patch("leash.client.requests.get")
    def test_get_env_missing_key_returns_none(self, mock_get):
        mock_get.return_value = _mock_response({"DB_URL": "postgres://..."})

        client = LeashIntegrations(auth_token="t")
        assert client.get_env("NONEXISTENT") is None


class TestConnections:
    @patch("leash.client.requests.get")
    def test_is_connected_true(self, mock_get):
        mock_get.return_value = _mock_response([
            {"providerId": "gmail", "status": "active"},
            {"providerId": "drive", "status": "inactive"},
        ])

        client = LeashIntegrations(auth_token="t")
        assert client.is_connected("gmail") is True

    @patch("leash.client.requests.get")
    def test_is_connected_false(self, mock_get):
        mock_get.return_value = _mock_response([
            {"providerId": "drive", "status": "inactive"},
        ])

        client = LeashIntegrations(auth_token="t")
        assert client.is_connected("gmail") is False

    @patch("leash.client.requests.get")
    def test_is_connected_on_error(self, mock_get):
        mock_get.side_effect = Exception("network error")

        client = LeashIntegrations(auth_token="t")
        assert client.is_connected("gmail") is False

    def test_get_connect_url(self):
        client = LeashIntegrations(auth_token="t", platform_url="https://leash.build")
        url = client.get_connect_url("gmail")
        assert url == "https://leash.build/api/integrations/connect/gmail"

    def test_get_connect_url_with_return(self):
        client = LeashIntegrations(auth_token="t", platform_url="https://leash.build")
        url = client.get_connect_url("gmail", return_url="https://myapp.com/settings")
        assert "return_url=" in url
        assert "myapp.com" in url


class TestMCP:
    @patch("leash.client.requests.post")
    def test_mcp_call(self, mock_post):
        mock_post.return_value = _mock_response({"result": "ok"})

        client = LeashIntegrations(auth_token="t", api_key="k")
        result = client.mcp("@mcp/server-notion", "search", {"query": "test"})

        assert result == {"result": "ok"}
        url = mock_post.call_args[0][0]
        assert "/api/mcp/run" in url

        body = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert body["package"] == "@mcp/server-notion"
        assert body["tool"] == "search"
        assert body["args"] == {"query": "test"}

    @patch("leash.client.requests.post")
    def test_mcp_error(self, mock_post):
        mock_post.return_value = _mock_response(
            {"error": "Package not found", "code": "not_found"},
            success=False,
        )

        client = LeashIntegrations(auth_token="t")
        with pytest.raises(LeashError):
            client.mcp("@mcp/nonexistent", "tool")
