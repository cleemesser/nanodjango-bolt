# not quite working!!! countlog is not implemented correctly

# /// script
# dependencies = ["nanodjango", "nanodjango-bolt"]
# ///

from nanodjango import Django
from nanodjango_bolt import BoltAPI
from django_bolt.responses import StreamingResponse

# pure django imports
from django.db import models

app = Django()
bolt = BoltAPI()


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
        headers={"Cache-Control": "no-cache"},
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
    app.run()  # run the django app, not sure if there is an equivalent call for django-bolt
