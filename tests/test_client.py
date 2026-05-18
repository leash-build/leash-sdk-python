"""Tests for the unified :class:`Leash` client.

Covers:

    - Constructor requires a request object (mirrors TS NO_REQUEST_SERVER_CONSTRUCT)
    - All four request shapes (Flask, Django, FastAPI/Starlette, raw dict)
      yield the same authenticated user
    - Authorization: Bearer header is captured into the bearer namespace
    - LEASH_API_KEY env-var precedence + explicit-arg override
    - LEASH_PLATFORM_URL env-var override
    - Context-manager and ``close()`` lifecycle
    - Public exports match the 0.4 surface
"""

from __future__ import annotations

import pytest

from leash import (
    IntegrationCaller,
    Leash,
    LeashError,
    LeashUser,
    get_leash_user,
    is_authenticated,
)


def test_requires_request() -> None:
    with pytest.raises(LeashError) as info:
        Leash()  # type: ignore[call-arg]
    assert info.value.code == "NO_REQUEST_SERVER_CONSTRUCT"


class TestRequestShapes:
    """Every framework request shape yields the same authenticated user."""

    def test_flask_request(self, flask_request, http_client_factory) -> None:
        client, _ = http_client_factory()
        with Leash(request=flask_request, http_client=client) as leash:
            user = leash.auth.user()
        assert isinstance(user, LeashUser)
        assert user.id == "user-123"
        assert user.email == "alice@example.com"

    def test_django_request(self, django_request, http_client_factory) -> None:
        client, _ = http_client_factory()
        with Leash(request=django_request, http_client=client) as leash:
            user = leash.auth.user()
        assert user is not None
        assert user.id == "user-123"

    def test_django_meta_only_request(self, token, http_client_factory) -> None:
        """Older Django wrappers expose only META — verify the fallback path."""
        from types import SimpleNamespace

        req = SimpleNamespace(META={"HTTP_COOKIE": f"leash-auth={token}"}, headers={})
        client, _ = http_client_factory()
        with Leash(request=req, http_client=client) as leash:
            user = leash.auth.user()
        assert user is not None
        assert user.email == "alice@example.com"

    def test_fastapi_request(self, fastapi_request, http_client_factory) -> None:
        client, _ = http_client_factory()
        with Leash(request=fastapi_request, http_client=client) as leash:
            user = leash.auth.user()
        assert user is not None
        assert user.id == "user-123"

    def test_plain_dict_request(self, header_dict_request, http_client_factory) -> None:
        client, _ = http_client_factory()
        with Leash(request=header_dict_request, http_client=client) as leash:
            user = leash.auth.user()
        assert user is not None
        assert user.id == "user-123"

    def test_request_without_cookie_returns_none(self, http_client_factory) -> None:
        from types import SimpleNamespace

        req = SimpleNamespace(cookies={}, headers={})
        client, _ = http_client_factory()
        with Leash(request=req, http_client=client) as leash:
            assert leash.auth.user() is None
            assert leash.auth.is_authenticated() is False


class TestBearerToken:
    def test_extracted_but_not_forwarded_on_integration_calls(
        self, token, http_client_factory, monkeypatch
    ) -> None:
        """Bearer token is captured off the request but NOT sent to integrations.

        Matches the TS SDK contract (leash-sdk-ts/src/leash.ts:586-601). The
        platform's verifyToken() can reject a user JWT before X-API-Key is
        checked, so integration POSTs intentionally carry only X-API-Key +
        Cookie.
        """
        from types import SimpleNamespace

        monkeypatch.delenv("LEASH_API_KEY", raising=False)
        req = SimpleNamespace(cookies={}, headers={"Authorization": f"Bearer {token}"})
        client, capture = http_client_factory(
            {("POST", "/api/integrations/gmail/list-messages"): (200, {"success": True, "data": {"messages": []}})}
        )
        with Leash(request=req, http_client=client) as leash:
            # The bearer token IS captured off the request (used by other code
            # paths) — but the integration call must not echo it.
            assert leash._bearer_token == token
            leash.integrations.gmail.list_messages()
        assert len(capture.requests) == 1
        sent = capture.requests[0].headers
        assert sent.get("authorization") is None
        # No api key either (we didn't set one) — only the cookie path would
        # carry auth here, and we sent no cookie. Verifies the integration call
        # surface stays minimal.
        assert sent.get("x-api-key") is None


class TestApiKeyPrecedence:
    def test_explicit_arg_wins(self, flask_request, http_client_factory, monkeypatch) -> None:
        monkeypatch.setenv("LEASH_API_KEY", "env-key")
        client, capture = http_client_factory(
            {("POST", "/api/integrations/gmail/list-messages"): (200, {"success": True, "data": {}})}
        )
        with Leash(request=flask_request, api_key="explicit-key", http_client=client) as leash:
            leash.integrations.gmail.list_messages()
        assert capture.requests[0].headers.get("x-api-key") == "explicit-key"

    def test_env_var_used_when_arg_missing(
        self, flask_request, http_client_factory, monkeypatch
    ) -> None:
        monkeypatch.setenv("LEASH_API_KEY", "env-key")
        client, capture = http_client_factory(
            {("POST", "/api/integrations/gmail/list-messages"): (200, {"success": True, "data": {}})}
        )
        with Leash(request=flask_request, http_client=client) as leash:
            leash.integrations.gmail.list_messages()
        assert capture.requests[0].headers.get("x-api-key") == "env-key"


class TestPlatformUrl:
    def test_default(self, flask_request, http_client_factory, monkeypatch) -> None:
        monkeypatch.delenv("LEASH_PLATFORM_URL", raising=False)
        client, capture = http_client_factory()
        with Leash(request=flask_request, http_client=client) as leash:
            leash.integrations.gmail.list_messages()
        url = str(capture.requests[0].url)
        assert url.startswith("https://leash.build/")

    def test_env_var_override(self, flask_request, http_client_factory, monkeypatch) -> None:
        monkeypatch.setenv("LEASH_PLATFORM_URL", "https://staging.leash.build/")
        client, capture = http_client_factory()
        with Leash(request=flask_request, http_client=client) as leash:
            leash.integrations.gmail.list_messages()
        url = str(capture.requests[0].url)
        assert url.startswith("https://staging.leash.build/")

    def test_explicit_arg_wins(self, flask_request, http_client_factory, monkeypatch) -> None:
        monkeypatch.setenv("LEASH_PLATFORM_URL", "https://env.leash.build")
        client, capture = http_client_factory()
        with Leash(
            request=flask_request,
            platform_url="https://explicit.leash.build/",
            http_client=client,
        ) as leash:
            leash.integrations.gmail.list_messages()
        url = str(capture.requests[0].url)
        assert url.startswith("https://explicit.leash.build/")


class TestForwardedCookie:
    def test_cookie_forwarded_to_platform(
        self, flask_request, http_client_factory, token
    ) -> None:
        client, capture = http_client_factory(
            {("POST", "/api/integrations/gmail/list-messages"): (200, {"success": True, "data": {}})}
        )
        with Leash(request=flask_request, http_client=client) as leash:
            leash.integrations.gmail.list_messages()
        cookie_header = capture.requests[0].headers.get("cookie", "")
        assert f"leash-auth={token}" in cookie_header


class TestExports:
    def test_public_surface(self) -> None:
        # Should not raise — and they should be the canonical objects.
        assert Leash is not None
        assert LeashError is not None
        assert LeashUser is not None
        assert IntegrationCaller is not None
        assert callable(get_leash_user)
        assert callable(is_authenticated)

    def test_provider_namespaces_wired(self, flask_request, http_client_factory) -> None:
        client, _ = http_client_factory()
        with Leash(request=flask_request, http_client=client) as leash:
            assert hasattr(leash.integrations, "gmail")
            assert hasattr(leash.integrations, "google_calendar")
            assert hasattr(leash.integrations, "google_drive")
            assert hasattr(leash.integrations, "linear")
            assert isinstance(leash.integrations.provider("slack"), IntegrationCaller)

    def test_ts_aliases_share_instance(self, flask_request, http_client_factory) -> None:
        """`calendar` / `drive` aliases match the TS surface."""
        client, _ = http_client_factory()
        with Leash(request=flask_request, http_client=client) as leash:
            assert leash.integrations.calendar is leash.integrations.google_calendar
            assert leash.integrations.drive is leash.integrations.google_drive

    def test_version_is_0_4(self) -> None:
        import leash

        assert leash.__version__.startswith("0.4")


class TestLifecycle:
    def test_context_manager_closes_http_client(
        self, flask_request, http_client_factory
    ) -> None:
        client, _ = http_client_factory()
        with Leash(request=flask_request, http_client=client) as leash:
            assert leash._http is client
        # We injected the client, so Leash should not close it
        assert not client.is_closed

    def test_owned_client_closed_on_close(self, flask_request) -> None:
        leash = Leash(request=flask_request)
        owned = leash._http
        leash.close()
        assert owned.is_closed
