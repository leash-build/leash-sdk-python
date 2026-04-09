"""Google Drive integration client."""

from typing import Any, Dict, Optional

from leash.types import CallFn


class DriveClient:
    """Client for Google Drive operations via the Leash platform proxy."""

    def __init__(self, call: CallFn):
        self._call = call

    def list_files(
        self,
        query: Optional[str] = None,
        max_results: int = 20,
        folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List files in the user's Drive.

        Args:
            query: Drive search query (Google Drive API query syntax).
            max_results: Maximum number of files to return.
            folder_id: Restrict to files within a specific folder.

        Returns:
            Dict with 'files' list.
        """
        params: Dict[str, Any] = {"maxResults": max_results}
        if query:
            params["query"] = query
        if folder_id:
            params["folderId"] = folder_id
        return self._call("google_drive", "list-files", params)

    def get_file(self, file_id: str) -> Dict[str, Any]:
        """Get file metadata by ID.

        Args:
            file_id: The file identifier.

        Returns:
            The file metadata object.
        """
        return self._call("google_drive", "get-file", {"fileId": file_id})

    def download_file(self, file_id: str) -> Any:
        """Download file content by ID.

        Args:
            file_id: The file identifier.

        Returns:
            The file content (format depends on file type).
        """
        return self._call("google_drive", "download-file", {"fileId": file_id})

    def create_folder(self, name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new folder.

        Args:
            name: Folder name.
            parent_id: Optional parent folder ID.

        Returns:
            The created folder metadata.
        """
        params: Dict[str, Any] = {"name": name}
        if parent_id:
            params["parentId"] = parent_id
        return self._call("google_drive", "create-folder", params)

    def upload_file(
        self,
        name: str,
        content: str,
        mime_type: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a file to Drive.

        Args:
            name: File name.
            content: File content (text or base64-encoded).
            mime_type: MIME type of the file (e.g. 'text/plain').
            parent_id: Optional parent folder ID.

        Returns:
            The created file metadata.
        """
        params: Dict[str, Any] = {"name": name, "content": content, "mimeType": mime_type}
        if parent_id:
            params["parentId"] = parent_id
        return self._call("google_drive", "upload-file", params)

    def delete_file(self, file_id: str) -> Dict[str, Any]:
        """Delete a file by ID.

        Args:
            file_id: The file identifier.

        Returns:
            Confirmation of deletion.
        """
        return self._call("google_drive", "delete-file", {"fileId": file_id})

    def search_files(self, query: str, max_results: int = 20) -> Dict[str, Any]:
        """Search files using a query string.

        Args:
            query: Search query (Google Drive API query syntax).
            max_results: Maximum number of results.

        Returns:
            Dict with 'files' list.
        """
        return self._call("google_drive", "search-files", {"query": query, "maxResults": max_results})
