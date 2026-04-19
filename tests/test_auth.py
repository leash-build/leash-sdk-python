"""Tests for leash.auth – framework-agnostic server authentication.

Covers:
- Flask-style request (request.cookies dict)
- Django-style request (request.META['HTTP_COOKIE'] and request.COOKIES)
- FastAPI/Starlette-style request (request.cookies mapping)
- Raw WSGI / generic headers (request.headers with 'cookie' key)
- Missing cookie raises LeashAuthError
- Expired token raises LeashAuthError
- Invalid / malformed token raises LeashAuthError
- Dev mode (no LEASH_JWT_SECRET) decodes without verification
- is_authenticated returns True/False
"""

import os
import time
from types import SimpleNamespace
from unittest.mock import patch

import jwt as pyjwt
import pytest

from leash.auth import LeashAuthError, LeashUser, get_leash_user, is_authenticated

SECRET = "test-secret-key"

PAYLOAD = {
    "sub": "user-123",
    "email": "alice@example.com",
    "name": "Alice",
    "picture": "https://example.com/alice.png",
}


def _make_token(payload=None, secret=SECRET, exp_offset=3600):
    """Create a signed HS256 JWT."""
    p = dict(payload or PAYLOAD)
    if exp_offset is not None:
        p["exp"] = int(time.time()) + exp_offset
    return pyjwt.encode(p, secret, algorithm="HS256")


def _expired_token():
    return _make_token(exp_offset=-10)


# ── Flask-style request ──────────────────────────────────────────────


class TestFlaskStyle:
    def test_extracts_user_from_cookies_dict(self):
        token = _make_token()
        req = SimpleNamespace(cookies={"leash-auth": token})
        with patch.dict(os.environ, {"LEASH_JWT_SECRET": SECRET}):
            user = get_leash_user(req)
        assert isinstance(user, LeashUser)
        assert user.id == "user-123"
        assert user.email == "alice@example.com"
        assert user.name == "Alice"
        assert user.picture == "https://example.com/alice.png"


# ── Django-style request ─────────────────────────────────────────────


class TestDjangoStyle:
    def test_extracts_from_meta_http_cookie(self):
        token = _make_token()
        # Django WSGI style: no .cookies, has .META with HTTP_COOKIE
        req = SimpleNamespace(
            META={"HTTP_COOKIE": f"leash-auth={token}; other=val"},
        )
        # Remove cookies attr so the first strategy falls through
        with patch.dict(os.environ, {"LEASH_JWT_SECRET": SECRET}):
            user = get_leash_user(req)
        assert user.id == "user-123"

    def test_extracts_from_django_cookies_dict(self):
        """Django also exposes request.COOKIES (uppercase) but we access
        via request.cookies (lowercase) which Django provides too."""
        token = _make_token()
        req = SimpleNamespace(cookies={"leash-auth": token})
        with patch.dict(os.environ, {"LEASH_JWT_SECRET": SECRET}):
            user = get_leash_user(req)
        assert user.email == "alice@example.com"


# ── FastAPI / Starlette-style request ────────────────────────────────


class TestFastAPIStyle:
    def test_extracts_from_starlette_cookies(self):
        """Starlette uses an immutable mapping for cookies, not a plain dict."""
        from collections import OrderedDict

        token = _make_token()
        cookies = OrderedDict({"leash-auth": token})
        req = SimpleNamespace(cookies=cookies)
        with patch.dict(os.environ, {"LEASH_JWT_SECRET": SECRET}):
            user = get_leash_user(req)
        assert user.id == "user-123"


# ── Raw WSGI / generic headers ───────────────────────────────────────


class TestRawWSGI:
    def test_extracts_from_headers_dict(self):
        token = _make_token()
        req = SimpleNamespace(
            headers={"cookie": f"leash-auth={token}; foo=bar"},
        )
        with patch.dict(os.environ, {"LEASH_JWT_SECRET": SECRET}):
            user = get_leash_user(req)
        assert user.id == "user-123"

    def test_case_insensitive_header_lookup(self):
        token = _make_token()
        req = SimpleNamespace(
            headers={"Cookie": f"leash-auth={token}"},
        )
        with patch.dict(os.environ, {"LEASH_JWT_SECRET": SECRET}):
            user = get_leash_user(req)
        assert user.email == "alice@example.com"


# ── Error cases ──────────────────────────────────────────────────────


class TestErrors:
    def test_missing_cookie_raises(self):
        req = SimpleNamespace(cookies={})
        with pytest.raises(LeashAuthError, match="Missing leash-auth cookie"):
            get_leash_user(req)

    def test_no_cookie_attr_raises(self):
        req = SimpleNamespace()
        with pytest.raises(LeashAuthError, match="Missing leash-auth cookie"):
            get_leash_user(req)

    def test_expired_token_raises(self):
        token = _expired_token()
        req = SimpleNamespace(cookies={"leash-auth": token})
        with patch.dict(os.environ, {"LEASH_JWT_SECRET": SECRET}):
            with pytest.raises(LeashAuthError, match="expired"):
                get_leash_user(req)

    def test_invalid_token_raises(self):
        req = SimpleNamespace(cookies={"leash-auth": "not-a-jwt"})
        with patch.dict(os.environ, {"LEASH_JWT_SECRET": SECRET}):
            with pytest.raises(LeashAuthError, match="Invalid token"):
                get_leash_user(req)

    def test_wrong_secret_raises(self):
        token = _make_token(secret="wrong-secret")
        req = SimpleNamespace(cookies={"leash-auth": token})
        with patch.dict(os.environ, {"LEASH_JWT_SECRET": SECRET}):
            with pytest.raises(LeashAuthError, match="Invalid token"):
                get_leash_user(req)


# ── Dev mode (no LEASH_JWT_SECRET) ───────────────────────────────────


class TestDevMode:
    def test_decodes_without_verification(self):
        token = _make_token(secret="any-secret-doesnt-matter")
        req = SimpleNamespace(cookies={"leash-auth": token})
        with patch.dict(os.environ, {}, clear=False):
            # Ensure LEASH_JWT_SECRET is not set
            os.environ.pop("LEASH_JWT_SECRET", None)
            user = get_leash_user(req)
        assert user.id == "user-123"
        assert user.email == "alice@example.com"

    def test_dev_mode_accepts_expired_token(self):
        """Without secret, signature and expiry are not verified."""
        token = _expired_token()
        req = SimpleNamespace(cookies={"leash-auth": token})
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LEASH_JWT_SECRET", None)
            # dev mode should not raise on expiry
            user = get_leash_user(req)
        assert user.id == "user-123"


# ── is_authenticated ─────────────────────────────────────────────────


class TestIsAuthenticated:
    def test_returns_true_for_valid_request(self):
        token = _make_token()
        req = SimpleNamespace(cookies={"leash-auth": token})
        with patch.dict(os.environ, {"LEASH_JWT_SECRET": SECRET}):
            assert is_authenticated(req) is True

    def test_returns_false_for_missing_cookie(self):
        req = SimpleNamespace(cookies={})
        assert is_authenticated(req) is False

    def test_returns_false_for_invalid_token(self):
        req = SimpleNamespace(cookies={"leash-auth": "garbage"})
        with patch.dict(os.environ, {"LEASH_JWT_SECRET": SECRET}):
            assert is_authenticated(req) is False

    def test_returns_false_for_expired_token(self):
        token = _expired_token()
        req = SimpleNamespace(cookies={"leash-auth": token})
        with patch.dict(os.environ, {"LEASH_JWT_SECRET": SECRET}):
            assert is_authenticated(req) is False
