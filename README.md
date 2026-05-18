# Leash SDK (Python)

Python SDK for the Leash platform. Construct a single `Leash()` client per
request and reach identity, env, and integrations through one object.

```bash
pip install leash-sdk
```

## Quick start

```python
from leash import Leash

# Pass the request object from your route handler.
# Works with Flask, FastAPI / Starlette, Django, and plain dict-style
# requests (anything that exposes cookies or headers).
leash = Leash(request=request)

# Identity - sync, returns None when not authenticated
user = leash.auth.user()
if user:
    print(user.email)

# Runtime env-var resolution from the Leash platform
api_key = leash.env.get("OPENAI_API_KEY")              # Optional[str]
api_key = leash.env.get("STRIPE_SECRET_KEY", fresh=True)
values = leash.env.get_many(["OPENAI_API_KEY", "STRIPE_KEY"])

# Integrations
messages = leash.integrations.gmail.list_messages(max_results=5)
issues = leash.integrations.linear.list_issues(state_type="started")
events = leash.integrations.google_calendar.list_events(
    time_min="2026-04-01T00:00:00Z",
    time_max="2026-04-30T00:00:00Z",
)
```

## The `Leash()` constructor

`Leash(request=...)` is server-only in 0.4. It accepts any framework
request object that exposes cookies or headers:

| Framework | What the SDK reads |
|---|---|
| Flask | `request.cookies['leash-auth']` |
| Django | `request.COOKIES['leash-auth']` or `request.META['HTTP_COOKIE']` |
| FastAPI / Starlette | `request.cookies.get('leash-auth')` |
| Raw / dict | `request['cookie']` or `request.headers['cookie']` |

`Authorization: Bearer <jwt>` headers are also recognised - used by the
CLI / agent flow.

### Authentication precedence

1. `LEASH_API_KEY` env var (server-only, never request-bound)
2. `Authorization: Bearer <jwt>` header on the request (CLI / agent)
3. `leash-auth` cookie on the request (browser to deployed app)

All three may coexist. The SDK forwards each in the appropriate header so
the platform can pick the right credential.

## Namespaces

### `leash.auth`

```python
user = leash.auth.user()                  # Optional[LeashUser]
authed = leash.auth.is_authenticated()    # bool
```

### `leash.env`

```python
value = leash.env.get("OPENAI_API_KEY")           # Optional[str]
value = leash.env.get("STRIPE_KEY", fresh=True)
mapping = leash.env.get_many(["A", "B", "C"])     # dict[str, Optional[str]]
```

Results are cached per `Leash` instance for 60 seconds.

`leash.env.get` requires `LEASH_API_KEY` to be set (env var or `api_key=`
constructor arg). Missing / not-declared keys return `None`; auth, plan,
and platform errors raise `LeashError`.

### `leash.integrations`

```python
leash.integrations.gmail.list_messages(max_results=5)
leash.integrations.gmail.send_message(to="x@y.com", subject="hi", body="...")

leash.integrations.google_calendar.list_events(time_min="...", time_max="...")
leash.integrations.google_calendar.create_event(
    summary="Sync", start={"dateTime": "..."}, end={"dateTime": "..."},
)

leash.integrations.google_drive.list_files(query="...")
leash.integrations.google_drive.upload_file(
    name="report.txt", content="...", mime_type="text/plain",
)

leash.integrations.linear.list_issues(state_type="started")
leash.integrations.linear.create_issue(team_id="...", title="...")
```

For providers without a typed wrapper yet (GitHub, HubSpot, Jira, Slack,
...) use the escape hatch:

```python
slack = leash.integrations.provider("slack")
slack.call("post-message", {"channel": "#general", "text": "hi"})
```

## Errors

Every SDK call raises a single error type: `LeashError`. It carries a
stable `code` plus a `message`, optional `action` (remediation hint),
`see_also` (docs URL), `status` (HTTP), and `cause`.

```python
from leash import Leash, LeashError

try:
    leash.integrations.gmail.list_messages()
except LeashError as err:
    if err.code == "CONNECTION_REQUIRED":
        print("Connect Gmail at:", err.see_also)
    elif err.code == "UPGRADE_REQUIRED":
        print("Upgrade required:", err.message)
    else:
        raise
```

Known codes: `NO_API_KEY`, `NO_REQUEST_SERVER_CONSTRUCT`, `UNAUTHORIZED`,
`NO_AUTH_CONTEXT`, `INTEGRATION_NOT_ENABLED`, `INTEGRATION_ERROR`,
`UPGRADE_REQUIRED`, `NETWORK_ERROR`, `KEY_NOT_DECLARED`, `INVALID_KEY`,
`SOURCE_RESYNC_FAILED`, `ENV_FETCH_ERROR`, `CONNECTION_REQUIRED`,
`PLAN_BLOCK`.

## Sync only in 0.4

The SDK uses `httpx`'s sync client. Async-first callers can wrap calls:

```python
import asyncio

messages = await asyncio.to_thread(
    leash.integrations.gmail.list_messages, max_results=5,
)
```

A native async surface is on the 0.4.1 roadmap.

## Lifecycle

`Leash` owns an internal `httpx.Client`. Either call `leash.close()` or
use it as a context manager:

```python
with Leash(request=request) as leash:
    user = leash.auth.user()
    msgs = leash.integrations.gmail.list_messages()
```

You can inject your own client with `Leash(request=..., http_client=...)`.

## Framework examples

### Flask

```python
from flask import Flask, request, jsonify
from leash import Leash

app = Flask(__name__)

@app.get("/me")
def me():
    leash = Leash(request=request)
    user = leash.auth.user()
    return jsonify({"user": user.__dict__ if user else None})
```

### FastAPI

```python
from fastapi import FastAPI, Request
from leash import Leash

app = FastAPI()

@app.get("/me")
async def me(request: Request):
    leash = Leash(request=request)
    user = leash.auth.user()
    return {"user": user.__dict__ if user else None}
```

### Django

```python
from django.http import JsonResponse
from leash import Leash

def me(request):
    leash = Leash(request=request)
    user = leash.auth.user()
    return JsonResponse({"user": user.__dict__ if user else None})
```

## License

Apache-2.0
