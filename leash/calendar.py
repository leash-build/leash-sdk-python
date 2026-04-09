"""Google Calendar integration client."""

from typing import Any, Dict, Optional

from leash.types import CallFn


class CalendarClient:
    """Client for Google Calendar operations via the Leash platform proxy."""

    def __init__(self, call: CallFn):
        self._call = call

    def list_calendars(self) -> Dict[str, Any]:
        """List all calendars accessible to the user.

        Returns:
            Dict with calendar list data.
        """
        return self._call("google_calendar", "list-calendars", {})

    def list_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """List events on a calendar.

        Args:
            calendar_id: Calendar identifier (default 'primary').
            time_min: Lower bound for event start time (RFC 3339, e.g. '2026-04-01T00:00:00Z').
            time_max: Upper bound for event start time (RFC 3339).
            max_results: Maximum number of events to return.

        Returns:
            Dict with 'items' list of events.
        """
        params: Dict[str, Any] = {"calendarId": calendar_id, "maxResults": max_results}
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        return self._call("google_calendar", "list-events", params)

    def get_event(self, calendar_id: str, event_id: str) -> Dict[str, Any]:
        """Get a single event by ID.

        Args:
            calendar_id: Calendar identifier.
            event_id: Event identifier.

        Returns:
            The event object.
        """
        return self._call("google_calendar", "get-event", {"calendarId": calendar_id, "eventId": event_id})

    def create_event(
        self,
        calendar_id: str = "primary",
        summary: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new calendar event.

        Args:
            calendar_id: Calendar identifier (default 'primary').
            summary: Event title.
            start: Start time (RFC 3339, e.g. '2026-04-10T10:00:00Z').
            end: End time (RFC 3339).
            description: Event description.

        Returns:
            The created event object.
        """
        params: Dict[str, Any] = {"calendarId": calendar_id}
        if summary:
            params["summary"] = summary
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if description:
            params["description"] = description
        return self._call("google_calendar", "create-event", params)
