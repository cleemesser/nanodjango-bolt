"""
Minimal nanodjango-bolt example with single-port serving.

Both Django views and BoltAPI routes are served on the same port by Actix.
Django views go through the ASGI bridge; BoltAPI routes are handled natively.

Run:
    python examples/helloworld.py runbolt --port 8000

Then visit:
    http://localhost:8000/           (Django view)
    http://localhost:8000/api/hello  (Bolt API)
    http://localhost:8000/api/greet?name=World
"""

from nanodjango import Django
from nanodjango_bolt import BoltAPI

app = Django()
bolt = BoltAPI()

# this is a django route (wsgi)
@app.route("/")
def home(request):
    return (
        "<h1>nanodjango-bolt example</h1><p>Try /api/hello or /api/greet?name=World</p>"
    )

# here are the bolt api routes

@bolt.get("/api/hello")
async def hello(request):
    return {"message": "hello from bolt"}


@bolt.get("/api/greet")
async def greet(request):
    name = request.GET.get("name", "stranger")
    return {"message": f"hello, {name}!"}


@bolt.post("/api/echo")
async def echo(request):
    import json

    body = json.loads(request.body)
    return {"you_sent": body}


# Register catch-all AFTER all bolt routes so they take priority.
# Unmatched requests (like /) are forwarded to Django's ASGI app.
bolt.mount_django(r'/')

# if __name__ == "__main__":
#     import sys
#     from django.core.management import execute_from_command_line

#     execute_from_command_line(sys.argv)
# o
