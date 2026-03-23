# How django-bolt's Admin ASGI Bridge Works

This document describes how django-bolt serves Django admin through its
Rust/Actix server using an ASGI bridge, and why this pattern can be
generalized to serve all Django views.

## Overview

django-bolt's Actix server only knows about routes explicitly registered via
`BoltAPI`. It has no built-in awareness of Django's URL routing. To serve
Django admin, django-bolt implements an ASGI bridge: a set of catch-all
Actix routes that forward requests to Django's ASGI application in-process.

The key files are in `django_bolt/admin/`:

- `asgi_bridge.py` — converts Actix requests to ASGI and calls Django
- `routes.py` — registers catch-all routes on BoltAPI
- `admin_detection.py` — detects the admin URL prefix from Django's urlconf

## Request flow

```
Browser → Actix Router → catch-all route matched → admin_handler()
  → ASGIFallbackHandler.handle_request(request)
    → actix_to_asgi_scope(request)      # convert PyRequest dict to ASGI scope
    → create_receive_callable(body)      # wrap body as ASGI receive channel
    → create_send_callable(holder)       # collect response via ASGI send channel
    → asgi_app(scope, receive, send)     # call Django's full ASGI app
  → (status, headers, body) returned to Actix
→ Response sent to browser
```

## Step 1: Route registration (`routes.py`)

The `AdminRouteRegistrar` registers routes directly into BoltAPI's internal
route list, bypassing the decorator API. This is important because admin
handlers don't go through the normal parameter-parsing dispatch path.

```python
# From routes.py — simplified
class AdminRouteRegistrar:
    def __init__(self, api: BoltAPI):
        self.api = api

    def register_routes(self, host, port):
        # Create the ASGI handler (shared by all admin routes)
        self.api._asgi_handler = ASGIFallbackHandler(host, port)

        # Register catch-all patterns for admin
        route_patterns = get_admin_route_patterns()
        # Returns: [("/admin", methods), ("/admin/", methods),
        #           ("/admin/{path:path}", methods)]

        for path_pattern, methods in route_patterns:
            for method in methods:
                self._register_admin_route(method, path_pattern)

    def _register_admin_route(self, method, path_pattern):
        # Create handler that delegates to ASGI bridge
        async def admin_handler(request):
            return await self.api._asgi_handler.handle_request(request)

        # Register directly into BoltAPI internals
        handler_id = self.api._next_handler_id
        self.api._next_handler_id += 1

        self.api._routes.append((method, path_pattern, handler_id, admin_handler))
        self.api._handlers[handler_id] = admin_handler

        # Metadata tells _dispatch to pass the raw request dict
        # (not parse path/query params like normal BoltAPI routes)
        self.api._handler_meta[handler_id] = {
            "mode": "request_only",
            "is_async": True,
            "sig": None,
            "fields": [],
            "default_status_code": 200,
            "response_type": None,
        }
```

Key details:

- **`{path:path}` syntax** — Actix's router treats this as a catch-all that
  matches any remaining path segments. `/admin/{path:path}` matches
  `/admin/login/`, `/admin/app/model/1/change/`, etc.
- **`mode: "request_only"`** — tells BoltAPI's `_dispatch` to pass the raw
  PyRequest dict to the handler instead of parsing parameters from the
  function signature.
- **Direct `_routes` manipulation** — bypasses the decorator to avoid BoltAPI's
  async enforcement and parameter compilation.

## Step 2: ASGI conversion (`asgi_bridge.py`)

The `ASGIFallbackHandler` converts django-bolt's PyRequest dict into an
ASGI3 scope and channels Django's full middleware stack.

### PyRequest → ASGI scope

```python
def actix_to_asgi_scope(request, server_host, server_port):
    path = request.get("path", "/")

    # Restore trailing slash stripped by Actix's NormalizePath::trim()
    # Django expects trailing slashes and will redirect without them
    if path != "/" and not path.endswith("/"):
        path = path + "/"

    # Convert query dict to URL-encoded string
    query_string = urlencode(sorted(request.get("query", {}).items()))

    # Convert headers dict to ASGI format: [(b"name", b"value")]
    headers = [(k.encode("latin1"), v.encode("latin1"))
               for k, v in request.get("headers", {}).items()]

    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": request.get("method", "GET").upper(),
        "path": path,
        "query_string": query_string.encode("latin1"),
        "headers": headers,
        "server": (server_host, server_port),
        # ... scheme, client, etc.
    }
```

### ASGI channels

**Receive channel** — sends the request body once, then blocks forever.
The "wait forever" behavior is critical: Django's ASGI handler races
`listen_for_disconnect()` against `process_request()`. If receive returns
a disconnect immediately, Django aborts the request.

```python
def create_receive_callable(body):
    sent = False
    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        await asyncio.Event().wait()  # block forever
    return receive
```

**Send channel** — collects `http.response.start` (status + headers) and
`http.response.body` (possibly chunked) into a response holder dict.

### Calling Django

```python
class ASGIFallbackHandler:
    async def handle_request(self, request):
        asgi_app = self._get_asgi_app()  # lazy: get_asgi_application()
        scope = actix_to_asgi_scope(request, self.server_host, self.server_port)
        receive = create_receive_callable(request.get("body", b""))
        response_holder = {"status": 200, "headers": [], "body": b""}
        send = create_send_callable(response_holder)

        await asgi_app(scope, receive, send)

        return (response_holder["status"],
                response_holder["headers"],
                response_holder["body"])
```

The return type `(status, headers, body)` is what BoltAPI's dispatch expects
from handlers with `mode: "request_only"`.

## Step 3: Server startup (`runbolt.py`)

In `start_single_process()`, admin routes are registered **after** all
BoltAPI routes are merged but **before** routes are passed to Rust:

```python
# 1. Autodiscover and merge BoltAPI instances
merged_api = self.merge_apis(apis)

# 2. Register OpenAPI routes
merged_api._register_openapi_routes()

# 3. Register admin routes (ASGI bridge)
merged_api._register_admin_routes(host, port)
merged_api._register_static_routes()

# 4. Pass all routes to Rust
rust_routes = []
for method, path, handler_id, handler in merged_api._routes:
    rust_routes.append((method, norm_path, handler_id, handler))
_core.register_routes(rust_routes)

# 5. Start Actix
_core.start_server_async(merged_api._dispatch, host, port, compression)
```

**Route ordering matters.** BoltAPI routes are registered first, admin
catch-all routes last. Actix's router matches the first registered route,
so explicit BoltAPI routes always take priority over the catch-all.

## Why this generalizes

The admin bridge has nothing admin-specific in its core mechanism. The
only admin-specific part is `get_admin_route_patterns()` which returns
`/admin/{path:path}`. Replace that with `/{path:path}` (matching
everything) and the same bridge serves all Django views.

The pattern is:

1. Register all BoltAPI routes first (they get priority)
2. Register a `/{path:path}` catch-all last
3. The catch-all handler forwards to `ASGIFallbackHandler`
4. Django's ASGI app handles URL routing, middleware, views, templates
5. The response flows back through Actix to the client

This gives you a single port serving both BoltAPI routes (handled by
Rust/Actix at native speed) and Django views (handled by Django's ASGI
app through the bridge).
