"""Cookie + JWT extraction across Python web frameworks.

Mirrors the multi-framework extraction strategy in
``leash-sdk-ts/src/server/auth.ts`` (``extractToken`` → ``getLeashUser``).
Never throws — returns ``None`` for any unexpected request shape so the
caller can decide how to react.

Frameworks supported in 0.4:

    - Flask: ``request.cookies`` is an :class:`ImmutableMultiDict`
    - Django: ``request.COOKIES`` dict or ``request.META['HTTP_COOKIE']``
    - FastAPI / Starlette: ``request.cookies`` mapping
    - Raw WSGI / dict-like: ``cookie`` header on a ``headers`` mapping

The same matrix applies to ``Authorization: Bearer …`` header extraction
(used by the CLI / agent auth flow).
"""

from __future__ import annotations

import os
from http.cookies import SimpleCookie
from typing import Any, Optional

from .errors import LeashError
from .types import LeashJWTPayload, LeashUser

COOKIE_NAME = "leash-auth"
AUTH_HEADER = "authorization"


# ---------------------------------------------------------------------------
# Cookie / header extraction
# ---------------------------------------------------------------------------


def _get_attr(obj: Any, name: str) -> Any:
    """Best-effort attribute / item lookup that never raises."""
    try:
        val = getattr(obj, name, None)
        if val is not None:
            return val
    except Exception:
        pass
    try:
        return obj[name]  # type: ignore[index]
    except Exception:
        return None


def _normalise_cookie_value(value: Any) -> Optional[str]:
    """Some frameworks wrap cookies in ``{value: str}``-style objects.

    Mirrors the TS ``_extractCookie`` normalisation block: when the returned
    cookie has a ``value`` attribute or key (Next.js ``RequestCookie``,
    ``http.cookies.Morsel``), unwrap it.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    # http.cookies.Morsel exposes ``.value``
    morsel_value = getattr(value, "value", None)
    if isinstance(morsel_value, str):
        return morsel_value
    # Dict-like with a 'value' key (Next.js RequestCookie shape, defensive)
    try:
        candidate = value["value"]  # type: ignore[index]
        if isinstance(candidate, str):
            return candidate
    except Exception:
        pass
    try:
        return str(value)
    except Exception:
        return None


def _from_cookie_jar(request: Any, name: str) -> Optional[str]:
    """Try framework cookie jars in priority order.

    1. ``request.cookies.get(name)`` — Flask, FastAPI/Starlette
    2. ``request.cookies[name]`` — dict-style (raw, some Django wrappers)
    3. ``request.COOKIES.get(name)`` — Django ``HttpRequest``
    """
    cookies = getattr(request, "cookies", None)
    if cookies is not None:
        getter = getattr(cookies, "get", None)
        if callable(getter):
            try:
                val = getter(name)
                normalised = _normalise_cookie_value(val)
                if normalised is not None:
                    return normalised
            except Exception:
                pass
        try:
            val = cookies[name]  # type: ignore[index]
            normalised = _normalise_cookie_value(val)
            if normalised is not None:
                return normalised
        except Exception:
            pass

    django_cookies = getattr(request, "COOKIES", None)
    if django_cookies is not None:
        try:
            val = django_cookies.get(name) if hasattr(django_cookies, "get") else django_cookies[name]
            normalised = _normalise_cookie_value(val)
            if normalised is not None:
                return normalised
        except Exception:
            pass

    return None


def _from_cookie_header(request: Any, name: str) -> Optional[str]:
    """Parse a raw ``Cookie`` header off any request-like object.

    Covers Django (``request.META['HTTP_COOKIE']``) and any framework that
    only exposes a ``headers`` mapping (Starlette before cookies are
    materialised, plain WSGI, raw ``dict``).
    """
    raw: Optional[str] = None

    # Django META
    meta = getattr(request, "META", None)
    if meta is not None:
        try:
            candidate = meta.get("HTTP_COOKIE") if hasattr(meta, "get") else meta["HTTP_COOKIE"]
            if isinstance(candidate, str) and candidate:
                raw = candidate
        except Exception:
            pass

    # Generic headers (Starlette, FastAPI, raw dict, etc.)
    if raw is None:
        headers = getattr(request, "headers", None)
        if headers is not None:
            raw = _header_lookup(headers, "cookie")

    # Caller passed a plain dict of headers (e.g. {"cookie": "..."})
    if raw is None and isinstance(request, dict):
        raw = _header_lookup(request, "cookie")

    if not raw:
        return None

    try:
        jar = SimpleCookie(raw)
        if name in jar:
            return jar[name].value
    except Exception:
        return None
    return None


def _header_lookup(headers: Any, name: str) -> Optional[str]:
    """Case-insensitive header lookup against any mapping or Headers-like."""
    lname = name.lower()

    getter = getattr(headers, "get", None)
    if callable(getter):
        try:
            val = getter(name)
            if isinstance(val, str) and val:
                return val
        except Exception:
            pass
        try:
            val = getter(lname)
            if isinstance(val, str) and val:
                return val
        except Exception:
            pass

    try:
        for key, value in headers.items():  # type: ignore[union-attr]
            if isinstance(key, str) and key.lower() == lname and isinstance(value, str):
                return value
    except Exception:
        pass

    return None


def extract_cookie(request: Any, name: str = COOKIE_NAME) -> Optional[str]:
    """Return the named cookie value off any request shape, or ``None``."""
    if request is None:
        return None
    try:
        return _from_cookie_jar(request, name) or _from_cookie_header(request, name)
    except Exception:
        return None


def extract_bearer_token(request: Any) -> Optional[str]:
    """Return the JWT off ``Authorization: Bearer …`` if present."""
    if request is None:
        return None
    headers = getattr(request, "headers", None)
    raw = None
    if headers is not None:
        raw = _header_lookup(headers, "authorization")
    if raw is None and isinstance(request, dict):
        raw = _header_lookup(request, "authorization")
    if not raw or not isinstance(raw, str):
        return None
    parts = raw.split(None, 1)
    if len(parts) != 2:
        return None
    scheme, token = parts
    if scheme.lower() != "bearer":
        return None
    return token.strip() or None


# ---------------------------------------------------------------------------
# JWT decoding
# ---------------------------------------------------------------------------


def _import_jwt():  # pragma: no cover - import wrapper
    try:
        import jwt  # type: ignore

        return jwt
    except ImportError as exc:
        raise LeashError(
            code="NO_AUTH_CONTEXT",
            message=(
                "PyJWT is required to decode the leash-auth cookie. "
                "Install with: pip install 'leash-sdk[jwt]' or pip install PyJWT."
            ),
            action="Add PyJWT to your dependencies (already a hard dep of leash-sdk).",
            see_also="https://leash.build/docs/sdk",
            cause=exc,
        ) from exc


def decode_token(token: str) -> LeashJWTPayload:
    """Decode the leash-auth JWT.

    When ``LEASH_JWT_SECRET`` is set, the token is verified (HS256). Without
    it the SDK falls back to ``verify_signature=False`` so local development
    works without provisioning the secret — the platform still controls
    issuance, so a malformed token gets rejected.

    Mirrors the dev-fallback in ``leash-sdk-ts/src/server/auth.ts``.
    """
    jwt = _import_jwt()
    secret = os.environ.get("LEASH_JWT_SECRET")

    try:
        if secret:
            return jwt.decode(token, secret, algorithms=["HS256"])
        return jwt.decode(token, options={"verify_signature": False})
    except jwt.ExpiredSignatureError as exc:  # type: ignore[attr-defined]
        raise LeashError(
            code="NO_AUTH_CONTEXT",
            message="leash-auth cookie has expired.",
            action="Re-open the app in the Leash dashboard to refresh the cookie.",
            see_also="https://leash.build/docs/sdk",
            cause=exc,
        ) from exc
    except jwt.InvalidTokenError as exc:  # type: ignore[attr-defined]
        raise LeashError(
            code="NO_AUTH_CONTEXT",
            message=f"Invalid leash-auth cookie: {exc}",
            action="Re-open the app in the Leash dashboard to mint a fresh cookie.",
            see_also="https://leash.build/docs/sdk",
            cause=exc,
        ) from exc


def payload_to_user(payload: LeashJWTPayload) -> LeashUser:
    """Convert a decoded JWT payload to a :class:`LeashUser`."""
    user_id = payload.get("userId") or payload.get("sub")
    if not user_id:
        raise LeashError(
            code="NO_AUTH_CONTEXT",
            message="leash-auth cookie is missing a user identifier.",
            action="Re-open the app in the Leash dashboard to mint a fresh cookie.",
            see_also="https://leash.build/docs/sdk",
        )
    return LeashUser(
        id=str(user_id),
        email=str(payload.get("email") or ""),
        name=str(payload.get("name") or ""),
        picture=payload.get("picture"),
    )


def get_leash_user(request: Any) -> LeashUser:
    """Decode the request's leash-auth cookie into a :class:`LeashUser`.

    Raises :class:`LeashError` when the cookie is missing or invalid. For
    a non-throwing variant, use :meth:`Leash.auth.user`.
    """
    token = extract_cookie(request)
    if not token:
        raise LeashError(
            code="NO_AUTH_CONTEXT",
            message="No leash-auth cookie on the request.",
            action=(
                "Construct Leash with a request from a route that runs behind the "
                "Leash platform, or open the app from the Leash dashboard to mint "
                "a fresh cookie."
            ),
            see_also="https://leash.build/docs/sdk",
        )
    return payload_to_user(decode_token(token))


def is_authenticated(request: Any) -> bool:
    """``True`` when :func:`get_leash_user` would return a user."""
    try:
        get_leash_user(request)
        return True
    except LeashError:
        return False


__all__ = [
    "COOKIE_NAME",
    "decode_token",
    "extract_bearer_token",
    "extract_cookie",
    "get_leash_user",
    "is_authenticated",
    "payload_to_user",
]
