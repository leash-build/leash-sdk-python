# Leash SDK (Python)

Python SDK for accessing platform integrations (Gmail, Google Calendar, Google Drive) from apps deployed on [Leash](https://leash.build).

## Install

```bash
pip install leash-sdk
```

## Usage

```python
from leash import LeashIntegrations

# Get the auth token from the leash-auth cookie (e.g. in Flask/Django)
integrations = LeashIntegrations(auth_token="your-jwt-token")

# Gmail
emails = integrations.gmail.list_messages(max_results=10)
integrations.gmail.send_message(to="user@example.com", subject="Hello", body="World")

# Calendar
events = integrations.calendar.list_events(time_min="2026-04-01T00:00:00Z")
integrations.calendar.create_event(
    summary="Meeting",
    start="2026-04-10T10:00:00Z",
    end="2026-04-10T11:00:00Z",
)

# Drive
files = integrations.drive.list_files(max_results=10)
integrations.drive.upload_file(name="notes.txt", content="hello", mime_type="text/plain")
```

## How it works

The SDK calls the Leash platform proxy at `https://leash.build/api/integrations/{provider}/{action}`. The platform handles all OAuth token management -- the SDK just passes the user's auth token and makes typed API calls.
