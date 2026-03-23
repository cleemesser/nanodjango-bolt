# nanodjango-bolt :  a prototype implementation

A [nanodjango](https://github.com/radiac/nanodjango) plugin that integrates
[django-bolt](https://github.com/dj-bolt/django-bolt) into single-file
Django apps. django-bolt gives you a production-ready Rust/Actix web server
without needing gunicorn, uvicorn, or a reverse proxy for your API routes.

This plugin handles all the settings wiring automatically -- you just import
`BoltAPI`from nanodjango_bolt  and start defining routes.

## Development install
```
pip install git+https://github.com/cleemesser/nanodjango-bolt.git
```

## (Eventual Standard) Installation
- has not been published to pypi yet
- as may be better to incorporate directly in django-bolt itself

```bash
pip install nanodjango-bolt
```
This will install nanodjango and its command line script

Or with uv:

```bash
uv add nanodjango-bolt
```

## Quickstart

```python
# myapp.py
from nanodjango import Django
from nanodjango_bolt import BoltAPI

app = Django()
bolt = BoltAPI()

@app.route("/")
def home(request):
    return "<h1>Hello from Django</h1>"

@bolt.get("/api/hello")
async def hello(request):
    return {"message": "hello world"}

@bolt.post("/api/items")
async def create_item(request):
    return {"id": 1, "status": "created"}

bolt.mount_django(r"/") # have bolt serve the django app too
```

Run the bolt server with nanodjango's CLI:

```bash
nanodjango manage myapp.py runbolt --port 8000
```

## What it does

Without this plugin, using django-bolt in a single-file nanodjango app requires
manually configuring `INSTALLED_APPS`, `BOLT_API`, and getting the import order
right (django-bolt must be imported after Django settings are configured).

nanodjango-bolt handles all of that:

- Adds `django_bolt` to `INSTALLED_APPS` automatically
- Configures `BOLT_API` (the setting that tells `runbolt` where to find your
  API instance) by detecting the variable name at decoration time
- Subclasses `django_bolt.BoltAPI` so `runbolt`'s autodiscovery accepts it
- Registers as a nanodjango plugin via setuptools entry points (no config needed)

## How it works

The plugin has two parts:

**`BoltAPI` subclass** -- A thin subclass of `django_bolt.api.BoltAPI`. When
you call `bolt = BoltAPI()` after `app = Django()`, it:

1. Creates a real django-bolt API instance (safe because Django is now configured)
2. Adds `django_bolt` to `INSTALLED_APPS`
3. On the first route decorator (`@bolt.get(...)`, etc.), scans the module
   globals to find the variable name and sets `settings.BOLT_API` accordingly

**Plugin hooks** -- Registered via setuptools entry point and loaded
automatically by nanodjango's pluggy-based plugin system:

- `django_pre_setup`: ensures `django_bolt` is in `INSTALLED_APPS` even if
  `BoltAPI()` is never called
- `convert_build_app_api`: supports `nanodjango convert` by detecting `BoltAPI`
  instances and route-decorated functions in the AST, moving them to `api.py`

## Running the server

django-bolt runs a Rust/Actix server, not Django's dev server.

**Single port** (Django views + Bolt API together):

Use `mount_django` to serve everything on one port. BoltAPI
routes are handled natively by Actix; all other requests are forwarded to
Django's ASGI application through an in-process bridge.

```python
from nanodjango import Django
from nanodjango_bolt import BoltAPI

app = Django()
api = BoltAPI()

@app.route("/")
def home(request):
    return "<h1>Hello from Django</h1>"

@api.get("/api/hello")
async def hello(request):
    return {"message": "hello from bolt"}

# If you want to serve the django app as well

api.mount_django(r"/") # this is part of django-bolt and allows for serving an ASGI

# Must be called AFTER all boltAPI routes are defined
```

Note also, because the file must be importable, do not name it with
non-importable characters like '-'.  that is, call it `myapp.py` not `my-app.py`


**Bolt only** (API routes served by Rust, no Django view fallback):

```bash
nanodjango manage myapp.py runbolt --dev --port 8000
# note if you have bolt.mount_django("/path") # then django will be served as well via http
```

**Separate ports** (Django views + Bolt API on different ports):
development mode
```bash
# Terminal 1 -- Django views
nanodjango run myapp.py --host localhost:8080
# or can do nanodjango manage myapp.py runserver --host localhost:8080
# Terminal 2 -- Bolt API
nandodjango myapp.py runbolt --port 8001
```

production mode:
```bash
# terminal 1
nanodjango serve myapp.py --host localhost:8080 # the django side with uvicorn

# second terminal
nanodjango manage myapp.py runbolt --port 8001 # [options for host port]

# setup of reverse proxy to serve to internet as usual
```

### runbolt options

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `0.0.0.0` | Host to bind to |
| `--port` | `8000` | Port to bind to |
| `--processes` | `1` | Number of worker processes |
| `--dev` | off | Auto-reload on file changes |
| `--no-admin` | off | Disable Django admin integration |
| `--backlog` | `1024` | Socket listen backlog |
| `--keep-alive` | OS default | HTTP keep-alive timeout (seconds) |

## Streaming responses (SSE / Datastar)

django-bolt's `StreamingResponse` works well with Server-Sent Events and
libraries like [datastar](https://data-star.dev/):

```python
from nanodjango import Django
from nanodjango_bolt import BoltAPI
from django_bolt.responses import StreamingResponse

app = Django()
bolt = BoltAPI()

@bolt.get("/stream")
async def stream(request):
    import asyncio

    async def generate():
        for i in range(5):
            yield f"data: message {i}\n\n".encode()
            await asyncio.sleep(1)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
```

## Converting to a full project

When you outgrow the single-file format:

```bash
nanodjango convert myapp.py /path/to/project --name=myproject
```

The `convert_build_app_api` hook detects `BoltAPI()` assignments and
`@bolt.get/post/...` decorated functions and moves them into `api.py` in the
generated project.

## Comparison: with and without the plugin

**Without nanodjango-bolt** (manual wiring):

```python
import sys
from django.conf import settings

settings.configure(
    DEBUG=True,
    SECRET_KEY="change-me",
    ROOT_URLCONF=__name__,
    INSTALLED_APPS=[
        "django.contrib.contenttypes",
        "django.contrib.auth",
        "django_bolt",
    ],
    BOLT_API=["__main__:api"],
)

from django_bolt import BoltAPI  # must be after settings.configure()

api = BoltAPI()

@api.get("/hello")
async def hello(request):
    return {"message": "hello"}

if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
```

**With nanodjango-bolt**:

```python
from nanodjango import Django
from nanodjango_bolt import BoltAPI

app = Django()
bolt = BoltAPI()

@bolt.get("/hello")
async def hello(request):
    return {"message": "hello"}
```

## automatically convert to full django project
following the nanodjango way, when project outgrows its single file , you can
convert it to a full Django site which uses [django-bolt](https://github.com/dj-bolt/django-bolt):

```bash
nanodjango convert myapp.py /path/to/project  --name=myprojectname
```

## Requirements

- Python >= 3.12
- nanodjango
- django-bolt

## Motivation
I learned about django-bolt recently and wanted to try out in different
scenarios. Using single-file apps is great for this so I started working it out
and will use it to see how well django-bolt plays with realtime and streaming
web apps and apis.

This is still a work in progress.
The next thing to do is to think about how to implement the "to full django" process that nanodjango offers.

## Todo:
- change name of project to follow nanodjango recommendations: `nanodjango-plugin-bolt`?
- see if makes sense to integrate plugin into django-bolt itself?


## Thanks
The many authors and contributors to django, django-bolt. Credit to claude code which helped with analyzing the nanodjango project.
made this much more practical to make a tool that would make my life a little
better.
