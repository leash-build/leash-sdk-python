# Leash SDK (Python)

Python SDK for accessing Leash-hosted integrations and MCP-backed tools.

This SDK talks to the Leash platform proxy, which handles:

- OAuth token storage
- provider routing
- MCP execution
- app env lookup

## Install

```bash
pip install leash-sdk
```

## Quick Start

```python
from leash import LeashIntegrations

client = LeashIntegrations(
    auth_token="your-platform-jwt",
    api_key="optional-app-api-key",
)

messages = client.gmail.list_messages(max_results=10)
events = client.calendar.list_events(time_min="2026-04-01T00:00:00Z")
files = client.drive.list_files(max_results=10)

env = client.get_env()
connected = client.is_connected("gmail")
```

## Default Platform URL

The default platform base URL is:

- `https://leash.build`

Requests are sent to routes such as:

- `https://leash.build/api/integrations/{provider}/{action}`
- `https://leash.build/api/apps/env`
- `https://leash.build/api/mcp/run`

## Supported Client Features

- Gmail actions
- Google Calendar actions
- Google Drive actions
- generic provider calls
- custom integration proxy calls
- connection status lookup
- connect URL generation
- app env fetch and caching
- MCP package execution via the platform

## Example

```python
from leash import LeashIntegrations

client = LeashIntegrations(auth_token="your-platform-jwt")

if not client.is_connected("gmail"):
    print(client.get_connect_url("gmail", return_url="https://myapp.example.com/settings"))
else:
    print(client.gmail.list_messages(max_results=5))
```

## Server Auth

The SDK includes helpers for authenticating users on the server side by reading
the `leash-auth` cookie set by the Leash platform.

```python
from leash import get_leash_user, is_authenticated

# Flask
@app.route('/me')
def me():
    user = get_leash_user(request)
    return jsonify({'id': user.id, 'email': user.email, 'name': user.name})
```

You can also check authentication without extracting the full user:

```python
if is_authenticated(request):
    # proceed
```

## MCP Calls

Use the client to execute MCP-backed tools through the platform:

```python
result = client.run_mcp(package="@some/mcp-package", tool="tool-name", args={"key": "value"})
```

## Notes

- `auth_token` should be a valid Leash platform JWT.
- `api_key` is optional, but useful for app-scoped env access and service-to-service usage.
- The SDK does not manage provider OAuth itself. It delegates that to the Leash platform.

## License

Apache-2.0
