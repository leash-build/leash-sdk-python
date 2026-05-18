"""Shared pytest fixtures for the Leash SDK test suite."""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

import httpx
import jwt as pyjwt
import pytest


SECRET = "test-secret-key"


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def make_token(
    *,
    payload: Optional[Dict[str, Any]] = None,
    secret: str = SECRET,
    exp_offset: Optional[int] = 3600,
) -> str:
    """Mint a signed HS256 JWT for tests."""
    body: Dict[str, Any] = {
        "sub": "user-123",
        "email": "alice@example.com",
        "name": "Alice",
        "picture": "https://example.com/alice.png",
    }
    if payload:
        body.update(payload)
    if exp_offset is not None:
        body["exp"] = int(time.time()) + exp_offset
    return pyjwt.encode(body, secret, algorithm="HS256")


@pytest.fixture
def token() -> str:
    return make_token()


@pytest.fixture(autouse=True)
def jwt_secret_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default to verified JWT decoding for every test."""
    monkeypatch.setenv("LEASH_JWT_SECRET", SECRET)


# ---------------------------------------------------------------------------
# Request fixtures — one per framework shape
# ---------------------------------------------------------------------------


@pytest.fixture
def flask_request(token: str) -> Any:
    """Flask: `request.cookies` is a dict-like with `.get`."""
    return SimpleNamespace(cookies={"leash-auth": token}, headers={})


@pytest.fixture
def django_request(token: str) -> Any:
    """Django: `request.COOKIES` plus `request.META['HTTP_COOKIE']`."""
    return SimpleNamespace(
        COOKIES={"leash-auth": token},
        META={"HTTP_COOKIE": f"leash-auth={token}; other=val"},
        headers={},
    )


@pytest.fixture
def fastapi_request(token: str) -> Any:
    """FastAPI / Starlette: dict-style cookies on `request.cookies`."""
    from collections import OrderedDict

    cookies = OrderedDict({"leash-auth": token})
    return SimpleNamespace(cookies=cookies, headers={})


@pytest.fixture
def header_dict_request(token: str) -> Dict[str, str]:
    """Plain dict with a `cookie` header — covers raw WSGI / lambda events."""
    return {"cookie": f"leash-auth={token}; foo=bar"}


# ---------------------------------------------------------------------------
# httpx transport stub
# ---------------------------------------------------------------------------


class _Capture:
    """Capture every request httpx sends through the stub transport."""

    def __init__(self) -> None:
        self.requests: List[httpx.Request] = []

    def __getitem__(self, idx: int) -> httpx.Request:
        return self.requests[idx]

    def __len__(self) -> int:
        return len(self.requests)

    def __iter__(self):
        return iter(self.requests)


def _make_handler(
    response_map: Dict[Tuple[str, str], Tuple[int, Any]],
    *,
    capture: _Capture,
    default: Tuple[int, Any] = (200, {"success": True, "data": {}}),
):
    def handler(req: httpx.Request) -> httpx.Response:
        capture.requests.append(req)
        key = (req.method.upper(), req.url.path)
        status, body = response_map.get(key, default)
        if isinstance(body, (dict, list)):
            return httpx.Response(status, json=body)
        return httpx.Response(status, content=body if isinstance(body, bytes) else str(body).encode())

    return handler


@pytest.fixture
def http_client_factory():
    """Build an ``httpx.Client`` backed by a programmable mock transport.

    Usage::

        client, capture = http_client_factory({
            ("POST", "/api/integrations/gmail/list-messages"): (200, {"success": True, "data": {"messages": []}}),
        })
    """

    def factory(
        response_map: Optional[Dict[Tuple[str, str], Tuple[int, Any]]] = None,
        *,
        default: Tuple[int, Any] = (200, {"success": True, "data": {}}),
    ) -> Tuple[httpx.Client, _Capture]:
        capture = _Capture()
        transport = httpx.MockTransport(
            _make_handler(response_map or {}, capture=capture, default=default)
        )
        return httpx.Client(transport=transport), capture

    return factory


__all__ = ["make_token", "SECRET"]
