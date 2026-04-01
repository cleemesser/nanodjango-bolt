# %%
from nanodjango import Django
from nanodjango_bolt import BoltAPI
from django_bolt.responses import StreamingResponse

# %%
app = Django()
bolt = BoltAPI()

# %%


@bolt.get("/stream")
async def stream(request):
    """send 5 messages, one every second, then end the stream"""
    import asyncio

    async def generate():
        for i in range(5):
            yield f"data: message {i}\n\n".encode()
            await asyncio.sleep(1)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Content-Encoding": "identity", "Cache-Control": "no-cache"},
    )


# a django route
@app.route("/")
def hello_world(request):
    return "<p>Hello, World!</p> <a href='/stream'>Go to stream</a>"


"""
Headers and query strings are forwarded in the ASGI scope.

## `mount_django()`

Mount Django's ASGI app under a prefix:

```python
from django_bolt import BoltAPI

api = BoltAPI()
api.mount_django("/django")
```

By default, this calls `django.core.asgi.get_asgi_application()`.
"""

bolt.mount_django("/")
