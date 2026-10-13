"""Every event listener the client supports, with the arguments each one receives.

You don't need all of these in a real bot - copy the ones you care about.

Run with:
    python examples/events.py
"""
import os
import asyncio

import vibes
from vibes import Client

client = Client(token=os.environ["VIBES_TOKEN"])


# --- Connection -------------------------------------------------------------

@client.event()
async def on_connect():
    """The socket is open and `client.user` is populated.

    Subscribe here: events only arrive for streamers you've subscribed to.
    """
    print(f"Logged in as {client.user}")
    for stream in await client.fetch_streams(limit=20):
        await client.subscribe_to(stream.channel)


# --- Chat -------------------------------------------------------------------

@client.event()
async def on_message(message: vibes.Message):
    """A chat message was sent in a stream you're subscribed to."""
    # `author` is None on system messages; `bot` marks bot accounts.
    if message.author is None:
        return
    print(f"[{message.stream.title}] {message.author}: {message.content}")


@client.event()
async def on_message_delete(message: vibes.Message):
    """A message was deleted.

    Only fires for messages the client has cached, so very old messages are
    skipped. The whole message is passed, not just an ID.
    """
    print(f"{message.author} deleted: {message.content!r}")


# --- Viewers ----------------------------------------------------------------

@client.event()
async def on_viewer_join(stream: vibes.Stream, viewer: vibes.User):
    """Someone started watching a subscribed stream.

    Anonymous viewers arrive as guests with `viewer.guest is True` and no ID.
    """
    print(f"{viewer} joined {stream.title}"
          f"{' (guest)' if viewer.guest else ''}")


@client.event()
async def on_viewer_leave(stream: vibes.Stream, viewer: vibes.User):
    """Someone stopped watching."""
    print(f"{viewer} left {stream.title}")


# --- Stream lifecycle -------------------------------------------------------

@client.event()
async def on_stream_online(stream: vibes.Stream):
    """A subscribed streamer went live."""
    print(f"{stream.channel} is live! {stream.title}")


@client.event()
async def on_stream_offline(stream: vibes.Stream):
    """A subscribed streamer ended their stream."""
    print(f"{stream.channel} stopped after {round(stream.duration / 60, 1)}min")


# --- Engagement -------------------------------------------------------------

@client.event()
async def on_new_follower(streamer: vibes.User, viewer: vibes.User):
    """A streamer you subscribe to gained a follower.

    Note the argument order: the streamer comes first, the follower second.
    """
    print(f"{viewer} followed {streamer}")


@client.event()
async def on_stream_like(stream: vibes.Stream, viewer: vibes.User):
    """Someone liked a stream."""
    print(f"{viewer} liked {stream.title} ({stream.likes} total)")


@client.event()
async def on_donation(donation: vibes.Donation):
    """A donation arrived."""
    print(f"{donation.user} donated {donation.amount} {donation.currency} "
          f"(~${donation.amount_usd}) to {donation.streamer}: {donation.message!r}")


# --- Internal ---------------------------------------------------------------

@client.event()
async def on_command_error(error):
    """A command failed. See examples/text_commands.py for a full handler."""
    print(f"command error: {error!r}")


@client.event()
async def _debug(raw: dict):
    """Every raw WebSocket frame, before it's parsed into an event.

    Handy when you're building something new and want to see what the server
    actually sends. The function is named `_debug` on purpose.
    """
    if raw.get("type") != "heartbeat":
        print("raw frame:", raw)


async def main():
    await client.start()


asyncio.run(main())
