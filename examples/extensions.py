"""Loading and unloading an extension at runtime.

The extension itself is in examples/example_extension.py.

Run from the repository root so that `examples` is importable:

    python -m examples.extensions

This bot loads the "greeter" extension on startup and exposes "!load" and
"!unload" commands, so you can add and remove its commands and listeners while
the client stays connected.
"""
import os
import asyncio

import vibes
from vibes import Client, commands
from vibes.commands import Context
from vibes.ext.errors import ExtensionNotFound, ExtensionAlreadyLoaded, ExtensionFailed

client = Client(token=os.environ["VIBES_TOKEN"], prefix="!")

EXTENSION = "examples.example_extension"


# --- A command that lives in the main bot, next to the extension -------------

@commands.command()
async def load(ctx: Context):
    """Load the extension back after it's been unloaded."""
    try:
        await client.load_extension(EXTENSION)
        await client.sync_commands()  # publish the extension's app commands
        await ctx.message.reply("Extension loaded!")
    except ExtensionAlreadyLoaded:
        await ctx.message.reply("It's already loaded.")


@commands.command()
async def unload(ctx: Context):
    """Remove the extension, its commands and its listeners."""
    try:
        await client.unload_extension(EXTENSION)
        await client.sync_commands()  # push the removed app commands to VIBES
        await ctx.message.reply("Extension unloaded!")
    except ExtensionNotFound:
        await ctx.message.reply("It isn't loaded.")


# --- Bot --------------------------------------------------------------------

@client.event()
async def on_connect():
    print(f"Logged in as {client.user}")

    try:
        await client.load_extension(EXTENSION)
    except ExtensionFailed as e:
        # Raised when the module or its setup() blows up on import.
        print(f"Failed to load the extension: {e}")
        return

    # Extensions often register app commands; push the merged list to VIBES.
    await client.sync_commands()

    for stream in await client.fetch_streams(limit=5):
        await client.subscribe_to(stream.channel)


@client.event()
async def on_message(message: vibes.Message):
    if message.author is None or message.author.bot:
        return
    if message.content.startswith(client.prefix):
        await client.process_commands(message)


async def main():
    # `start()` blocks for the lifetime of the bot. Use "!unload" and "!load" in
    # chat to add and remove the extension while it's running.
    await client.start()


asyncio.run(main())
