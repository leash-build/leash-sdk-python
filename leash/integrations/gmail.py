"""Gmail integration — mirrors ``leash.integrations.gmail`` in TS."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, cast

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
        return cast(GmailMessageList, self._call("list-messages", params or None))

    def get_message(self, message_id: str, *, format: GmailFormat = "full") -> Dict[str, Any]:
        return cast(Dict[str, Any], self._call("get-message", {"messageId": message_id, "format": format}))

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
        return cast(Dict[str, Any], self._call("send-message", params))

    def search_messages(
        self, query: str, *, max_results: Optional[int] = None
    ) -> GmailMessageList:
        params: Dict[str, Any] = {"query": query}
        if max_results is not None:
            params["maxResults"] = max_results
        return cast(GmailMessageList, self._call("search-messages", params))

    def list_labels(self) -> GmailLabelList:
        return cast(GmailLabelList, self._call("list-labels"))

    def get_profile(self) -> Dict[str, Any]:
        return cast(Dict[str, Any], self._call("get-profile"))


__all__ = ["GmailIntegration"]
