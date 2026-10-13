"""Native VIBES app commands - registered with the API instead of parsed from chat.

Unlike text commands, these show up in the VIBES command UI with a description
and per-option descriptions, and the server parses the arguments for you.

Run with:
    python examples/app_commands.py
"""
import os
import random
import asyncio

import vibes
from vibes import Client, commands
from vibes.commands import Context, CommandError

client = Client(token=os.environ["VIBES_TOKEN"])


# --- Commands ---------------------------------------------------------------

@commands.app_command()
@commands.describe(
    name="Your name",
    age="Your age in years",
    friend="A VIBES user to introduce alongside you",
)
async def intro(ctx: Context, name: str, age: int, friend: vibes.Viewer = None):
    """Introduce yourself to the chat."""  # <- this docstring is the command description
    text = f"{ctx.author} is {name}, {age} years old."
    if friend is not None:
        # `Viewer` is a supported option type for app commands (shown as "user"),
        # and gives you the full user object rather than just a name.
        text += f" Their friend is {friend.mention}!"
    await ctx.message.reply(text)


@commands.app_command(name="roll", description="Roll a die with a custom number of sides")
@commands.describe(sides="How many sides the die has")
async def roll_dice(ctx: Context, sides: int = 6):
    """The name and description can be overridden explicitly.

    Options with a default are optional, so the UI won't require `sides`.
    """
    await ctx.message.reply(f"🎲 {random.randint(1, sides)} (d{sides})")


@commands.app_command(role=vibes.Role.MOD)
async def modtools(ctx: Context):
    """Only moderators and the streamer see this command."""
    await ctx.message.reply("Mod tools go here.")


# --- Plumbing ---------------------------------------------------------------

@client.event()
async def on_connect():
    print(f"Logged in as {client.user}")

    # Push the registered app commands to VIBES. Do this on every startup so
    # the server has your current command list, then subscribe to any live
    # streams you want events from.
    synced = await client.sync_commands()
    print(f"Synced {len(synced)} app command(s): {', '.join(str(c) for c in synced)}")

    for stream in await client.fetch_streams(limit=5):
        await client.subscribe_to(stream.channel)


@client.event()
async def on_command_error(error):
    """App command failures arrive here, same as text commands.

    `ctx.invocation_id` (the invocation ID from the server) is available on the
    context if you need to reference the specific invocation.
    """
    if isinstance(error, CommandError):
        print(f"command error: {type(error).__name__} on invocation {error.context.invocation_id}")
    else:
        print(f"unexpected error: {error!r}")


async def main():
    await client.start()


asyncio.run(main())
