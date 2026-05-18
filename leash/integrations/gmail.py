"""Gmail integration — mirrors ``leash.integrations.gmail`` in TS."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from ..types import GmailLabelList, GmailMessageList
from .base import _BaseProvider

GmailFormat = Literal["full", "metadata", "minimal", "raw"]


class GmailIntegration(_BaseProvider):
    provider = "gmail"

    def list_messages(
        self,
        *,
        query: Optional[str] = None,
        max_results: Optional[int] = None,
        label_ids: Optional[List[str]] = None,
        page_token: Optional[str] = None,
    ) -> GmailMessageList:
        params: Dict[str, Any] = {}
        if query is not None:
            params["query"] = query
        if max_results is not None:
            params["maxResults"] = max_results
        if label_ids is not None:
            params["labelIds"] = label_ids
        if page_token is not None:
            params["pageToken"] = page_token
        return self._call("list-messages", params or None)  # type: ignore[return-value]

    def get_message(self, message_id: str, *, format: GmailFormat = "full") -> Dict[str, Any]:
        return self._call("get-message", {"messageId": message_id, "format": format})  # type: ignore[return-value]

    def send_message(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"to": to, "subject": subject, "body": body}
        if cc is not None:
            params["cc"] = cc
        if bcc is not None:
            params["bcc"] = bcc
        return self._call("send-message", params)  # type: ignore[return-value]

    def search_messages(
        self, query: str, *, max_results: Optional[int] = None
    ) -> GmailMessageList:
        params: Dict[str, Any] = {"query": query}
        if max_results is not None:
            params["maxResults"] = max_results
        return self._call("search-messages", params)  # type: ignore[return-value]

    def list_labels(self) -> GmailLabelList:
        return self._call("list-labels")  # type: ignore[return-value]

    def get_profile(self) -> Dict[str, Any]:
        return self._call("get-profile")  # type: ignore[return-value]


__all__ = ["GmailIntegration"]
