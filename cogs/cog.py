import vibes
from vibes import commands
from vibes.commands import Context
from vibes.ext import Extension
from vibes.ext import event_listener


class MyExtension(Extension):

    def __init__(self, client):
        self.client: vibes.Client = client

    async def ext_load(self):
        print("EXT LOADED!")

    async def ext_unload(self):
        print("EXT UNLOADED!")

    @event_listener()
    async def on_connect(self):
        print("Connected sucessfully!")

    @event_listener()
    async def on_message(self, message):
        print(message.author, message.content)

    @commands.command()
    async def ping(self, ctx: Context):
        await ctx.message.reply("Pong!")

async def setup(client):
    await client.add_ext(MyExtension(client))