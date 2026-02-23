"""
Minimal nanodjango-bolt example.

Run:
    python examples/hello.py runbolt --port 8000

Then visit:
    http://localhost:8000/api/hello
    http://localhost:8000/api/greet?name=World
"""

from nanodjango import Django
from nanodjango_bolt import BoltAPI

app = Django()
bolt = BoltAPI()


@app.route("/")
def home(request):
    return "<h1>nanodjango-bolt example</h1><p>Try /api/hello or /api/greet?name=World</p>"


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
