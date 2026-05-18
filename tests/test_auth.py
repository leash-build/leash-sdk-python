"""Tests for cookie + JWT extraction across frameworks."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from leash import LeashError
from leash.auth import (
    decode_token,
    extract_bearer_token,
    extract_cookie,
    get_leash_user,
    is_authenticated,
    payload_to_user,
)
from tests.conftest import SECRET, make_token


class TestExtractCookie:
    def test_flask_style(self, token) -> None:
        req = SimpleNamespace(cookies={"leash-auth": token})
        assert extract_cookie(req) == token

    def test_django_meta(self, token) -> None:
        req = SimpleNamespace(META={"HTTP_COOKIE": f"leash-auth={token}; x=y"})
        assert extract_cookie(req) == token

    def test_django_cookies_upper(self, token) -> None:
        req = SimpleNamespace(COOKIES={"leash-auth": token})
        assert extract_cookie(req) == token

    def test_headers_dict(self, token) -> None:
        req = SimpleNamespace(headers={"cookie": f"leash-auth={token}"})
        assert extract_cookie(req) == token

    def test_headers_case_insensitive(self, token) -> None:
        req = SimpleNamespace(headers={"Cookie": f"leash-auth={token}"})
        assert extract_cookie(req) == token

    def test_plain_dict(self, token) -> None:
        assert extract_cookie({"cookie": f"leash-auth={token}"}) == token

    def test_none(self) -> None:
        assert extract_cookie(None) is None

    def test_missing(self) -> None:
        req = SimpleNamespace(cookies={})
        assert extract_cookie(req) is None

    def test_morsel_style_value(self, token) -> None:
        from http.cookies import Morsel

        morsel: Morsel = Morsel()
        morsel.set("leash-auth", token, token)
        req = SimpleNamespace(cookies={"leash-auth": morsel})
        assert extract_cookie(req) == token


class TestExtractBearer:
    def test_basic(self) -> None:
        req = SimpleNamespace(headers={"Authorization": "Bearer my-token"})
        assert extract_bearer_token(req) == "my-token"

    def test_lowercase(self) -> None:
        req = SimpleNamespace(headers={"authorization": "bearer my-token"})
        assert extract_bearer_token(req) == "my-token"

    def test_dict(self) -> None:
        assert extract_bearer_token({"authorization": "Bearer abc"}) == "abc"

    def test_missing(self) -> None:
        req = SimpleNamespace(headers={})
        assert extract_bearer_token(req) is None

    def test_non_bearer(self) -> None:
        req = SimpleNamespace(headers={"authorization": "Basic abc"})
        assert extract_bearer_token(req) is None


class TestDecodeToken:
    def test_decodes_with_secret(self, token) -> None:
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["email"] == "alice@example.com"

    def test_expired_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        expired = make_token(exp_offset=-10)
        with pytest.raises(LeashError) as info:
            decode_token(expired)
        assert info.value.code == "NO_AUTH_CONTEXT"
        assert "expired" in info.value.message.lower()

    def test_wrong_secret_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bad = make_token(secret="other-secret")
        with pytest.raises(LeashError) as info:
            decode_token(bad)
        assert info.value.code == "NO_AUTH_CONTEXT"

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(LeashError) as info:
            decode_token("not-a-jwt")
        assert info.value.code == "NO_AUTH_CONTEXT"

    def test_dev_mode_skips_verification(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # No LEASH_JWT_SECRET -> dev fallback
        monkeypatch.delenv("LEASH_JWT_SECRET", raising=False)
        unsigned = make_token(secret="something-else")
        payload = decode_token(unsigned)
        assert payload["sub"] == "user-123"


class TestPayloadToUser:
    def test_basic(self) -> None:
        user = payload_to_user(
            {"sub": "u1", "email": "a@b.c", "name": "A", "picture": "x"}
        )
        assert user.id == "u1"
        assert user.picture == "x"

    def test_prefers_userid(self) -> None:
        user = payload_to_user(
            {"userId": "primary", "sub": "fallback", "email": "a@b.c", "name": "A"}
        )
        assert user.id == "primary"

    def test_missing_id_raises(self) -> None:
        with pytest.raises(LeashError) as info:
            payload_to_user({"email": "a@b.c", "name": "A"})
        assert info.value.code == "NO_AUTH_CONTEXT"


class TestGetLeashUser:
    def test_returns_user(self, token) -> None:
        req = SimpleNamespace(cookies={"leash-auth": token})
        user = get_leash_user(req)
        assert user.email == "alice@example.com"

    def test_missing_cookie_raises(self) -> None:
        req = SimpleNamespace(cookies={})
        with pytest.raises(LeashError) as info:
            get_leash_user(req)
        assert info.value.code == "NO_AUTH_CONTEXT"


class TestIsAuthenticated:
    def test_true(self, token) -> None:
        req = SimpleNamespace(cookies={"leash-auth": token})
        assert is_authenticated(req) is True

    def test_false_missing(self) -> None:
        req = SimpleNamespace(cookies={})
        assert is_authenticated(req) is False

    def test_false_invalid(self) -> None:
        req = SimpleNamespace(cookies={"leash-auth": "garbage"})
        assert is_authenticated(req) is False
