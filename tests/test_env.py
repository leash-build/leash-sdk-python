"""Tests for the ``leash.env`` namespace.

Covers:

    - ``get`` returns string value
    - ``get_many`` resolves multiple keys
    - 60s TTL cache (no second HTTP call within window)
    - ``fresh=True`` bypasses the cache read but still writes back
    - 404 returns ``None`` (Python-idiom adaptation of TS ``KEY_NOT_DECLARED``)
    - 401 / 402 / 400 / 502 raise the expected ``LeashError`` codes
    - ``LEASH_API_KEY`` requirement is enforced before any HTTP call
"""

from __future__ import annotations

import time
from types import SimpleNamespace

import httpx
import pytest

from leash import Leash, LeashError


def _client_returning(map_):
    captures = []

    def handler(req: httpx.Request) -> httpx.Response:
        captures.append(req)
        status, body = map_.get(req.url.path, (500, {}))
        return httpx.Response(status, json=body)

    return httpx.Client(transport=httpx.MockTransport(handler)), captures


def _build_leash(http_client, *, api_key="lsk_live_abc") -> Leash:
    req = SimpleNamespace(cookies={}, headers={})
    return Leash(request=req, api_key=api_key, http_client=http_client)


class TestGet:
    def test_returns_value(self) -> None:
        client, captures = _client_returning(
            {"/api/apps/me/secrets/OPENAI_API_KEY": (200, {"value": "sk-test"})}
        )
        with _build_leash(client) as leash:
            assert leash.env.get("OPENAI_API_KEY") == "sk-test"
        assert len(captures) == 1
        assert captures[0].headers.get("authorization") == "Bearer lsk_live_abc"

    def test_returns_none_on_404(self) -> None:
        client, _ = _client_returning(
            {"/api/apps/me/secrets/MISSING": (404, {})}
        )
        with _build_leash(client) as leash:
            assert leash.env.get("MISSING") is None

    def test_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("LEASH_API_KEY", raising=False)
        client, _ = _client_returning({})
        leash = Leash(
            request=SimpleNamespace(cookies={}, headers={}),
            http_client=client,
        )
        with pytest.raises(LeashError) as info:
            leash.env.get("ANYTHING")
        assert info.value.code == "NO_API_KEY"


class TestGetMany:
    def test_resolves_multiple(self) -> None:
        client, _ = _client_returning(
            {
                "/api/apps/me/secrets/A": (200, {"value": "1"}),
                "/api/apps/me/secrets/B": (200, {"value": "2"}),
                "/api/apps/me/secrets/MISSING": (404, {}),
            }
        )
        with _build_leash(client) as leash:
            result = leash.env.get_many(["A", "B", "MISSING"])
        assert result == {"A": "1", "B": "2", "MISSING": None}


class TestCache:
    def test_cache_hit(self) -> None:
        client, captures = _client_returning(
            {"/api/apps/me/secrets/X": (200, {"value": "v1"})}
        )
        with _build_leash(client) as leash:
            leash.env.get("X")
            leash.env.get("X")
            leash.env.get("X")
        # Only the first call should reach the network
        assert len(captures) == 1

    def test_fresh_bypasses_cache(self) -> None:
        calls = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(200, json={"value": f"v{calls['n']}"})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with _build_leash(client) as leash:
            assert leash.env.get("X") == "v1"
            assert leash.env.get("X") == "v1"             # cache hit
            assert leash.env.get("X", fresh=True) == "v2" # bypasses read
            assert leash.env.get("X") == "v2"             # served from fresh write-back
        assert calls["n"] == 2

    def test_cache_writes_back_on_404(self) -> None:
        client, captures = _client_returning(
            {"/api/apps/me/secrets/MISSING": (404, {})}
        )
        with _build_leash(client) as leash:
            assert leash.env.get("MISSING") is None
            assert leash.env.get("MISSING") is None
        assert len(captures) == 1  # None is cached just like a value


class TestErrors:
    def test_400_invalid_key(self) -> None:
        client, _ = _client_returning(
            {"/api/apps/me/secrets/BAD": (400, {"error": "invalid"})}
        )
        with _build_leash(client) as leash:
            with pytest.raises(LeashError) as info:
                leash.env.get("BAD")
        assert info.value.code == "INVALID_KEY"
        assert info.value.status == 400

    def test_401_unauthorized(self) -> None:
        client, _ = _client_returning(
            {"/api/apps/me/secrets/X": (401, {"error": "bad key"})}
        )
        with _build_leash(client) as leash:
            with pytest.raises(LeashError) as info:
                leash.env.get("X")
        assert info.value.code == "UNAUTHORIZED"

    def test_402_upgrade_required(self) -> None:
        client, _ = _client_returning(
            {"/api/apps/me/secrets/X": (402, {"requiredPlan": "growth"})}
        )
        with _build_leash(client) as leash:
            with pytest.raises(LeashError) as info:
                leash.env.get("X")
        assert info.value.code == "UPGRADE_REQUIRED"
        assert "growth" in info.value.message.lower()

    def test_502_source_resync(self) -> None:
        client, _ = _client_returning(
            {"/api/apps/me/secrets/X": (502, {"error": "aws timeout"})}
        )
        with _build_leash(client) as leash:
            with pytest.raises(LeashError) as info:
                leash.env.get("X")
        assert info.value.code == "SOURCE_RESYNC_FAILED"
        assert "aws timeout" in info.value.message

    def test_unexpected_status(self) -> None:
        client, _ = _client_returning(
            {"/api/apps/me/secrets/X": (503, {})}
        )
        with _build_leash(client) as leash:
            with pytest.raises(LeashError) as info:
                leash.env.get("X")
        assert info.value.code == "ENV_FETCH_ERROR"

    def test_value_missing_from_body(self) -> None:
        client, _ = _client_returning(
            {"/api/apps/me/secrets/X": (200, {})}
        )
        with _build_leash(client) as leash:
            with pytest.raises(LeashError) as info:
                leash.env.get("X")
        assert info.value.code == "ENV_FETCH_ERROR"
