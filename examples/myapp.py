# nanodjango manage myapp.py migrate
# nanodjanog manage myapp.py runbolt --dev

from nanodjango import Django
from nanodjango_bolt import BoltAPI

app = Django()
bolt = BoltAPI()


@app.route("/")
def home(request):
    return "<h1>Hello from Django</h1>"


@bolt.get("/api/hello")
async def hello(request):
    return {"message": "hello world from bolt"}


@bolt.post("/api/items")
async def create_item():
    return {"id": 1, "status": "created"} # fake creating an item


bolt.mount_django(r"/")  # allow bolt to also serve the django app
