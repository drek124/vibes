"""Chat commands: typed parameters, roles, cooldowns and error handling.

Text commands are parsed out of chat messages, so the client needs a `prefix`
and you must forward messages to `client.process_commands`.

Try in chat:
    !hello Ada
    !hello Ada Lovelace
    !donate 10 Have a good one
    !coinflip

Run with:
    python examples/text_commands.py
"""
import os
import random
import asyncio
import logging

import vibes
from vibes import Client, commands
from vibes.commands import (
    Context,
    CommandError,
    CommandNotFound,
    BadArgument,
    MissingArguments,
    NoPermission,
    OnCooldown,
)

logging.basicConfig(level=logging.INFO)

client = Client(token=os.environ["VIBES_TOKEN"], prefix="!")


# --- Commands ---------------------------------------------------------------

@commands.command()
async def hello(ctx: Context, name: str = "world"):
    """The simplest command: no required arguments.

    `!hello` -> "Hello, world!", `!hello Ada` -> "Hello, Ada!" and
    `!hello Ada Lovelace` -> "Hello, Ada Lovelace!" - leftover words are merged
    into the last parameter.
    """
    await ctx.message.reply(f"Hello, {name}!")


@commands.command()
async def donate(ctx: Context, amount: int, message: str = "No message"):
    """Parameters are typed from their annotations.

    `!donate abc` fails the `int` conversion and raises BadArgument.
    Because `message` is the last parameter, it soaks up the rest of the line:
    `!donate 10 Have a good one` -> amount=10, message="Have a good one".
    """
    await ctx.message.reply(f"Thanks for the {amount}! ({message})")


@commands.command(role=vibes.Role.MOD)
async def purge(ctx: Context):
    """Only moderators and the streamer can run this (`!purge`).

    The client compares `ctx.author.role` against the required role and raises
    NoPermission for everyone below it.
    """
    await ctx.message.reply("Purging! (not really)")


@commands.command(cooldown=commands.Cooldown(period=30, max_uses=2, target=commands.Cooldown.USER))
async def coinflip(ctx: Context):
    """At most 2 uses per 30 seconds, per user across every stream.

    Cooldown targets:
      Cooldown.VIEWER - one viewer in one chat (default)
      Cooldown.USER   - one user, everywhere
      Cooldown.CHAT   - the whole chat, shared by everyone
    """
    await ctx.message.reply(f"It's {random.choice(['heads', 'tails'])}!")


# --- Plumbing ---------------------------------------------------------------

@client.event()
async def on_connect():
    print(f"Logged in as {client.user}")


@client.event()
async def on_message(message: vibes.Message):
    # Ignore system messages and bots before doing anything else.
    if message.author is None or message.author.bot:
        return

    # Hand any prefixed message to the command framework. It validates the
    # command, permissions, arguments and cooldown, then calls the callback.
    if message.content.startswith(client.prefix):
        await client.process_commands(message)


@client.event()
async def on_command_error(error: Exception):
    """All command failures land here instead of raising out of process_commands.

    User mistakes arrive as a CommandError with a `.context`
    (`ctx.message`, `ctx.author`, `ctx.command`, ...); bugs in your command
    arrive as whatever exception the callback raised.
    """
    if not isinstance(error, CommandError):
        logging.exception("Unexpected error while running a command", exc_info=error)
        return

    ctx = error.context

    if isinstance(error, CommandNotFound):
        await ctx.message.reply("That command doesn't exist.")

    elif isinstance(error, BadArgument):
        # `error.parameter` is the CommandParameter that failed to convert.
        await ctx.message.reply(f"`{error.parameter.name}` isn't a valid value.")

    elif isinstance(error, MissingArguments):
        await ctx.message.reply("You're missing a required argument.")

    elif isinstance(error, NoPermission):
        await ctx.message.reply(
            f"That needs the {ctx.command.required_role.name} role or higher."
        )

    elif isinstance(error, OnCooldown):
        await ctx.message.reply(
            f"Only {error.cooldown.max_uses} use(s) per {error.cooldown.period}s - "
            f"try again in {error.available_after:.1f}s."
        )


async def main():
    await client.start()


asyncio.run(main())
