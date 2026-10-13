"""A self-contained extension: its own commands, listeners and lifecycle hooks.

Extensions live in their own importable module (they can't be defined in
__main__) and expose a module-level `setup(client)` coroutine. Everything an
extension registers - commands and listeners alike - is removed again when it's
unloaded.

See examples/extensions.py for the bot that loads this.
"""
import vibes
from vibes import commands
from vibes.commands import Context
from vibes.ext import Extension, event_listener


class Greeter(Extension):
    def __init__(self, client):
        self.client: vibes.Client = client

    # --- Lifecycle ----------------------------------------------------------

    async def ext_load(self):
        """Called right after the extension's commands & listeners are registered."""
        print("[greeter] loaded")

    async def ext_unload(self):
        """Called when the extension is unloaded - clean up here."""
        print("[greeter] unloaded")

    # --- Events -------------------------------------------------------------
    # Inside an extension, use @event_listener() instead of @client.event().
    # It takes the same optional event name.

    @event_listener()
    async def on_connect(self):
        print(f"[greeter] connected as {self.client.user}")

    @event_listener()
    async def on_stream_online(self, stream: vibes.Stream):
        print(f"[greeter] {stream.channel} just went live!")

    @event_listener()
    async def on_viewer_join(self, stream: vibes.Stream, viewer: vibes.User):
        if viewer.guest:
            return
        # Extensions can talk to the chat like any other part of the bot.
        await stream.chat.send(f"Welcome to {stream.title}, {viewer.mention}!")

    # --- Commands -----------------------------------------------------------
    # The decorators work exactly like they do outside an extension, except the
    # callback takes `self` before `ctx`.

    @commands.command()
    async def greet(self, ctx: Context, name: str = None):
        """A plain text command: "!greet Ada"."""
        await ctx.message.reply(f"Hi {name or ctx.author.mention}! :D")

    @commands.command(role=vibes.Role.MOD, cooldown=commands.Cooldown(10, 3, commands.Cooldown.CHAT))
    async def announce(self, ctx: Context, message: str):
        """A mod-only command with a chat-wide cooldown."""
        await ctx.chat.send(f"📣 {message}")

    @commands.app_command()
    @commands.describe(who="The viewer to wave at")
    async def wave(self, ctx: Context, who: vibes.Viewer):
        """Waves at someone."""
        await ctx.message.reply(f"👋 {who.mention}")


async def setup(client):
    """The entry point `load_extension` looks for."""
    await client.add_ext(Greeter(client))
