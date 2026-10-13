"""The smallest useful VIBES bot: connect, subscribe to live streams, and reply in chat.

Run with:
    python examples/quickstart.py

Requires a VIBES_TOKEN environment variable (see the README).
"""
import os
import asyncio

import vibes
from vibes import Client

TOKEN = os.environ["VIBES_TOKEN"]

# `prefix` is only needed if you want text commands ("!ping").
client = Client(token=TOKEN, prefix="!")


@client.event()
async def on_connect():
    # `client.user` is a ClientUser and is only available once we're connected.
    print(f"Logged in as {client.user}")

    # Ask VIBES which streams are live right now, then subscribe to each of them.
    # Events for subscribed streamers (chat, follows, likes, donations, ...) start flowing after this.
    for stream in await client.fetch_streams(limit=10):
        print(f"{stream.channel} is live: {stream.title!r} "
              f"({stream.viewers} viewers, {round(stream.duration / 60, 1)}min)")
        await client.subscribe_to(stream.channel)


@client.event()
async def on_message(message: vibes.Message):
    # System messages (joins, follows, ...) have no author.
    if message.author is None or message.author.bot:
        return

    print(f"[{message.stream.title}] {message.author}: {message.content}")

    if message.content == "!ping":
        # Sending a message returns the created Message object.
        sent = await message.reply("Pong!")
        print(f"  -> replied with {sent.id}")


async def main():
    # start() keeps the connection open and blocks until the socket closes.
    await client.start()


asyncio.run(main())
