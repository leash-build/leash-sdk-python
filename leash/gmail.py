"""Gmail integration client."""

from typing import Any, Dict, List, Optional

from leash.types import CallFn


class GmailClient:
    """Client for Gmail operations via the Leash platform proxy."""

    def __init__(self, call: CallFn):
        self._call = call

    def list_messages(
        self,
        query: Optional[str] = None,
        max_results: int = 20,
        label_ids: Optional[List[str]] = None,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List messages in the user's mailbox.

        Args:
            query: Gmail search query (e.g. 'from:user@example.com').
            max_results: Maximum number of messages to return.
            label_ids: Filter by label IDs (e.g. ['INBOX']).
            page_token: Token for fetching the next page of results.

        Returns:
            Dict with 'messages', 'nextPageToken', and 'resultSizeEstimate'.
        """
        params: Dict[str, Any] = {"maxResults": max_results}
        if query:
            params["query"] = query
        if label_ids:
            params["labelIds"] = label_ids
        if page_token:
            params["pageToken"] = page_token
        return self._call("gmail", "list-messages", params)

    def get_message(self, message_id: str, format: str = "full") -> Dict[str, Any]:
        """Get a single message by ID.

        Args:
            message_id: The message ID.
            format: Response format ('full', 'metadata', 'minimal', 'raw').

        Returns:
            The full message object.
        """
        return self._call("gmail", "get-message", {"messageId": message_id, "format": format})

    def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an email message.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            body: Email body text.
            cc: CC recipient(s).
            bcc: BCC recipient(s).

        Returns:
            The sent message metadata.
        """
        params: Dict[str, Any] = {"to": to, "subject": subject, "body": body}
        if cc:
            params["cc"] = cc
        if bcc:
            params["bcc"] = bcc
        return self._call("gmail", "send-message", params)

    def search_messages(self, query: str, max_results: int = 20) -> Dict[str, Any]:
        """Search messages using a Gmail query string.

        Args:
            query: Gmail search query.
            max_results: Maximum number of results to return.

        Returns:
            Dict with 'messages', 'nextPageToken', and 'resultSizeEstimate'.
        """
        return self._call("gmail", "search-messages", {"query": query, "maxResults": max_results})

    def list_labels(self) -> Dict[str, Any]:
        """List all labels in the user's mailbox.

        Returns:
            Dict with 'labels' list.
        """
        return self._call("gmail", "list-labels", {})
