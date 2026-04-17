# %%
import asyncio
from nanodjango import Django
from nanodjango_bolt import BoltAPI
from django_bolt.responses import StreamingResponse
from django_bolt.middleware import no_compress
# %%
app = Django()
bolt = BoltAPI()

# %%


@bolt.get("/stream")
@no_compress # don't compress streaming responses - batches them together
async def stream(request)-> StreamingResponse:
    """send 5 messages, one every second, then end the stream"""
    async def generate():
        for i in range(5):
            yield f"data: message {i} asyncio.sleep(1)\n\n".encode()
            await asyncio.sleep(1)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )


# a django route
@app.route("/")
def hello_world(request):
    return "<p>Hello, World!</p> <a href='/stream'>Go to stream</a>"


bolt.mount_django("/") # use bolt to serve django asgi app

if __name__ == "__main__":
    import sys # noqa: E402

    # needs to be imported after other things are configured
    # (single-file django app style)
    from django.core.management import (  # noqa: E402
        execute_from_command_line,
    )

    execute_from_command_line(sys.argv)
