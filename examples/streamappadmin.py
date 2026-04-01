# not quite working!!! countlog is not implemented correctly

# /// script
# dependencies = ["nanodjango", "nanodjango-bolt"]
# ///
import asyncio
from nanodjango import Django
from nanodjango_bolt import BoltAPI
from django_bolt.responses import StreamingResponse

# pure django imports
from django.db import models

app = Django()
bolt = BoltAPI()

# In your django-bolt api.py


@bolt.get("/stream")
async def stream(request):
    """send 5 messages, one every 0.5 second, then end the stream"""

    async def event_generator():
        for i in range(5):
            yield f"data: message {i} asyncio.sleep(0.5)\n\n".encode()
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # "Cache-Control": "no-cache",
            # "X-Accel-Buffering" : 'no', # this stops nginx buffering
            "Content-Encoding": "identity",  # this last header is essential to see streaming, it tells django-bolt to leave things unchanged
        },
    )


# a django route
@app.route("/")
def hello_world(request):
    return """<p>Hello, World!</p> <a href='/stream'>Go to stream</a>
    <a href='/count'>Go to count></a>
    <a href='/admin/'>Go to admin></a>
    """


# class CountLog(models.Model):
#    timestamp = models.DataTimeField(auto_now_add=True)


# quickie way to add admin for a model with nanodjango decorator
# the admin site will register itself at the url /admin/
@app.admin(list_display=["id", "timestamp"])
class CountLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)


@app.route("/count/")
def count(request):
    CountLog.objects.create()
    return "<p>Counted! Check the admin to see the log.</p>"


# Headers and query strings are forwarded in the ASGI scope.
# `mount_django()`

# By default, this calls `django.core.asgi.get_asgi_application()`.
# in order to get the django app

bolt.mount_django("/")


if __name__ == "__main__":
    import sys

    # needs to be imported after other things are configured
    # (single-file django app style)
    from django.core.management import (  # noqa: E402
        execute_from_command_line,
    )

    execute_from_command_line(sys.argv)

    #app.run()  # run the django app, not sure if there is an equivalent call for django-bolt
