"""Tests for the :class:`LeashError` exception type."""

from __future__ import annotations

from leash import LeashError


def test_stores_all_fields() -> None:
    cause = RuntimeError("upstream")
    err = LeashError(
        code="INTEGRATION_ERROR",
        message="something broke",
        action="try again",
        see_also="https://leash.build/docs",
        status=500,
        cause=cause,
    )
    assert err.code == "INTEGRATION_ERROR"
    assert err.message == "something broke"
    assert err.action == "try again"
    assert err.see_also == "https://leash.build/docs"
    assert err.status == 500
    assert err.cause is cause
    assert err.__cause__ is cause
    assert str(err) == (
        "x something broke\n  Fix: try again\n  See: https://leash.build/docs"
    )


def test_minimal() -> None:
    err = LeashError(code="UNAUTHORIZED", message="nope")
    assert err.code == "UNAUTHORIZED"
    assert err.action is None
    assert err.see_also is None
    assert str(err) == "x nope"


def test_is_exception() -> None:
    err = LeashError(code="X", message="y")
    assert isinstance(err, Exception)
