"""Google Calendar integration — mirrors ``leash.integrations.calendar`` in TS.

Named ``google_calendar`` (not ``calendar``) on the Python side to avoid
shadowing the stdlib :mod:`calendar` module — and to match the platform
provider id, which is also ``google_calendar``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..types import CalendarEvent, CalendarEventList, CalendarList
from .base import _BaseProvider


class GoogleCalendarIntegration(_BaseProvider):
    provider = "google_calendar"

    def list_calendars(self) -> CalendarList:
        return self._call("list-calendars")  # type: ignore[return-value]

    def list_events(
        self,
        *,
        calendar_id: Optional[str] = None,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: Optional[int] = None,
        query: Optional[str] = None,
        single_events: Optional[bool] = None,
        order_by: Optional[str] = None,
    ) -> CalendarEventList:
        params: Dict[str, Any] = {}
        if calendar_id is not None:
            params["calendarId"] = calendar_id
        if time_min is not None:
            params["timeMin"] = time_min
        if time_max is not None:
            params["timeMax"] = time_max
        if max_results is not None:
            params["maxResults"] = max_results
        if query is not None:
            params["query"] = query
        if single_events is not None:
            params["singleEvents"] = single_events
        if order_by is not None:
            params["orderBy"] = order_by
        return self._call("list-events", params or None)  # type: ignore[return-value]

    def create_event(
        self,
        *,
        summary: str,
        start: Dict[str, Any],
        end: Dict[str, Any],
        calendar_id: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[Dict[str, str]]] = None,
    ) -> CalendarEvent:
        params: Dict[str, Any] = {"summary": summary, "start": start, "end": end}
        if calendar_id is not None:
            params["calendarId"] = calendar_id
        if description is not None:
            params["description"] = description
        if location is not None:
            params["location"] = location
        if attendees is not None:
            params["attendees"] = attendees
        return self._call("create-event", params)  # type: ignore[return-value]

    def get_event(self, event_id: str, *, calendar_id: Optional[str] = None) -> CalendarEvent:
        params: Dict[str, Any] = {"eventId": event_id}
        if calendar_id is not None:
            params["calendarId"] = calendar_id
        return self._call("get-event", params)  # type: ignore[return-value]


__all__ = ["GoogleCalendarIntegration"]
