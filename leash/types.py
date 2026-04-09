"""Shared types for the Leash SDK."""

from typing import Any, Callable, Dict, Optional


class LeashError(Exception):
    """Raised when a Leash platform API call fails."""

    def __init__(self, message: str, code: Optional[str] = None, connect_url: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.connect_url = connect_url


# Type alias for the internal call function passed to provider clients.
CallFn = Callable[[str, str, Optional[Dict[str, Any]]], Any]
