"""Google Drive integration — mirrors ``leash.integrations.drive`` in TS."""

from __future__ import annotations

from typing import Any, Dict, Optional, cast

from ..types import DriveFile, DriveFileList
from .base import _BaseProvider


class GoogleDriveIntegration(_BaseProvider):
    provider = "google_drive"

    def list_files(
        self,
        *,
        query: Optional[str] = None,
        max_results: Optional[int] = None,
        folder_id: Optional[str] = None,
    ) -> DriveFileList:
        params: Dict[str, Any] = {}
        if query is not None:
            params["query"] = query
        if max_results is not None:
            params["maxResults"] = max_results
        if folder_id is not None:
            params["folderId"] = folder_id
        return cast(DriveFileList, self._call("list-files", params or None))

    def get_file(self, file_id: str) -> DriveFile:
        return cast(DriveFile, self._call("get-file", {"fileId": file_id}))

    def download_file(self, file_id: str) -> Any:
        return self._call("download-file", {"fileId": file_id})

    def create_folder(self, name: str, *, parent_id: Optional[str] = None) -> DriveFile:
        params: Dict[str, Any] = {"name": name}
        if parent_id is not None:
            params["parentId"] = parent_id
        return cast(DriveFile, self._call("create-folder", params))

    def upload_file(
        self,
        *,
        name: str,
        content: str,
        mime_type: str,
        parent_id: Optional[str] = None,
    ) -> DriveFile:
        params: Dict[str, Any] = {"name": name, "content": content, "mimeType": mime_type}
        if parent_id is not None:
            params["parentId"] = parent_id
        return cast(DriveFile, self._call("upload-file", params))

    def delete_file(self, file_id: str) -> Any:
        return self._call("delete-file", {"fileId": file_id})

    def search_files(self, query: str, *, max_results: Optional[int] = None) -> DriveFileList:
        params: Dict[str, Any] = {"query": query}
        if max_results is not None:
            params["maxResults"] = max_results
        return cast(DriveFileList, self._call("search-files", params))


__all__ = ["GoogleDriveIntegration"]
