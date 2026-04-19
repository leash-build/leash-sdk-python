"""Framework-agnostic server auth for Leash.

Reads the ``leash-auth`` cookie from any Python web framework request object
(Flask, Django, FastAPI/Starlette, raw WSGI) without importing any framework.
"""

import os
from dataclasses import dataclass
from http.cookies import SimpleCookie
from typing import Any, Optional

import jwt

from leash.types import LeashError

COOKIE_NAME = "leash-auth"


class LeashAuthError(LeashError):
    """Raised when authentication via the leash-auth cookie fails."""

    def __init__(self, message: str):
        super().__init__(message, code="auth_error")


@dataclass
class LeashUser:
    """Authenticated Leash user extracted from the JWT."""

    id: str
    email: str
    name: str
    picture: str


def _extract_cookie(request: Any) -> Optional[str]:
    """Try every known cookie-access pattern and return the token or None."""

    # 1. Flask / Django / Starlette: request.cookies as dict-like
    try:
        cookies = request.cookies
        if isinstance(cookies, dict):
            val = cookies.get(COOKIE_NAME)
            if val is not None:
                return str(val)
        else:
            # Starlette cookies are an immutable mapping, not a plain dict
            val = cookies.get(COOKIE_NAME)  # type: ignore[union-attr]
            if val is not None:
                return str(val)
    except (AttributeError, TypeError):
        pass

    # 2. Django WSGI: request.META['HTTP_COOKIE']
    try:
        raw = request.META.get("HTTP_COOKIE", "")  # type: ignore[union-attr]
        if raw:
            sc = SimpleCookie(raw)
            if COOKIE_NAME in sc:
                return sc[COOKIE_NAME].value
    except (AttributeError, TypeError):
        pass

    # 3. Generic headers dict: request.headers['cookie']
    try:
        headers = request.headers
        raw = None
        if isinstance(headers, dict):
            # Case-insensitive lookup
            for k, v in headers.items():
                if k.lower() == "cookie":
                    raw = v
                    break
        else:
            raw = headers.get("cookie")  # type: ignore[union-attr]
        if raw:
            sc = SimpleCookie(raw)
            if COOKIE_NAME in sc:
                return sc[COOKIE_NAME].value
    except (AttributeError, TypeError):
        pass

    return None


def _decode_token(token: str) -> dict:
    """Decode (and optionally verify) the JWT."""
    secret = os.environ.get("LEASH_JWT_SECRET")

    if secret:
        try:
            return jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise LeashAuthError("Token has expired")
        except jwt.InvalidTokenError as exc:
            raise LeashAuthError(f"Invalid token: {exc}")
    else:
        # Dev mode – decode without verification
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except jwt.InvalidTokenError as exc:
            raise LeashAuthError(f"Invalid token: {exc}")


def get_leash_user(request: Any) -> LeashUser:
    """Extract and return the authenticated :class:`LeashUser` from *request*.

    Works with Flask, Django, FastAPI/Starlette, and plain WSGI request
    objects.  Raises :class:`LeashAuthError` if the cookie is missing or the
    token is invalid.
    """
    token = _extract_cookie(request)
    if token is None:
        raise LeashAuthError("Missing leash-auth cookie")

    payload = _decode_token(token)

    return LeashUser(
        id=payload.get("sub", ""),
        email=payload.get("email", ""),
        name=payload.get("name", ""),
        picture=payload.get("picture", ""),
    )


def is_authenticated(request: Any) -> bool:
    """Return ``True`` if *request* contains a valid leash-auth cookie."""
    try:
        get_leash_user(request)
        return True
    except LeashAuthError:
        return False
