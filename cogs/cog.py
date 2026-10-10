import vibes
from vibes.ext import Extension
from vibes.ext import event_listener


class MyExtension(Extension):

    def __init__(self, client):
        self.client: vibes.Client = client

    async def cog_load(self):
        print("Cog is now loaded!")

    @event_listener()
    async def on_connect(self):
        print("Connected sucessfully!")


async def setup(client):
    await client.add_ext(MyExtension(client))