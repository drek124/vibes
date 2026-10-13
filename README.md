# VIBES Client

An async Python wrapper for the [VIBES](https://vibes.stream/) streaming API — REST endpoints, a realtime
WebSocket client, a typed command framework, and a plugin (extension) system.

```python
import os
import asyncio
import vibes
from vibes import Client

client = Client(token=os.environ["VIBES_TOKEN"], prefix="!")

@client.event()
async def on_message(message: vibes.Message):
    if message.content == "!ping":
        await message.reply("Pong!")

asyncio.run(client.start())
```

---

## Table of contents

- [Features](#features)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Clients](#clients)
  - [PassiveClient (REST only)](#passiveclient-rest-only)
  - [Client (WebSocket)](#client-websocket)
- [Events](#events)
- [Commands](#commands)
  - [Text commands](#text-commands)
  - [Parameters](#parameters)
  - [Roles](#roles)
  - [Cooldowns](#cooldowns)
  - [App commands](#app-commands)
  - [Error handling](#error-handling)
- [Extensions](#extensions)
- [Models reference](#models-reference)
- [Examples](#examples)
- [License](#license)

## Features

- **REST API** — fetch streams, users and your own application with `PassiveClient`.
- **Realtime events** — a WebSocket connection with automatic reconnects and 30s heartbeats.
- **Typed commands** — both classic chat (`!command`) and native VIBES *app commands*, with automatic
  argument parsing, role gating and per-viewer/user/chat cooldowns.
- **Extensions** — load and unload self-contained modules of commands and listeners at runtime.
- **Caching** — users and messages are cached to cut down on API calls.

## Installation

Python 3.11+ is required. Dependencies are `httpx` and `websockets`.

From a checkout:

```bash
pip install .
```

For development:

```bash
pip install -e .
```

## Quickstart

Grab an API token from your [VIBES dashboard](https://vibes.stream/dashboard/plugins/api) and export it
as `VIBES_TOKEN` (the examples read it from the environment, e.g. with a `.env` file and `python-dotenv`).

```python
import os
import asyncio
import vibes
from vibes import Client

client = Client(token=os.environ["VIBES_TOKEN"], prefix="!")

@client.event()
async def on_connect():
    print(f"Logged in as {client.user}")                     # ClientUser
    for stream in await client.fetch_streams(limit=10):
        await client.subscribe_to(stream.channel)            # listen to this stream

@client.event()
async def on_message(message: vibes.Message):
    if message.content.startswith("!"):
        await client.process_commands(message)               # let the command framework run

asyncio.run(client.start())
```

`Client.start()` opens the WebSocket and runs the event loop until the connection closes — it is the
last thing you await, and it blocks for the lifetime of the bot.

## Clients

### PassiveClient (REST only)

No WebSocket, no events — just authenticated API calls. Use it for scripts, cron jobs or dashboards.

```python
import vibes

api = vibes.PassiveClient(token=TOKEN)
try:
    app = await api.fetch_client()
    print(app.owner, app.rate_limit)

    streams = await api.fetch_streams(limit=50, category="chit-chat")
    user = await api.fetch_user("some-streamer")   # None if not found
finally:
    await api.close()
```

| Method | Returns | Notes |
| --- | --- | --- |
| `fetch_client()` | `Application` | Your own app: owner, key, rate limit, webhook. |
| `fetch_streams(*, limit=100, category=None, mature=True)` | `list[Stream]` | `category` accepts a slug or a `StreamCategory`. `mature=True` requests 18+ streams (403 if your account isn't 18+). |
| `fetch_user(slug)` | `User \| None` | Accepts a username or ID. Results are cached. |
| `send_request(coro, *args, raise_for_status=True, **kwargs)` | `httpx.Response` | The low-level call every method is built on. |
| `close()` | `None` | Closes the underlying `httpx.AsyncClient`. |
| `clear_cache()` | `None` | Empties the user and message caches. |

`send_request` gives you rate-limit handling and typed errors for free:

- `429` responses are retried automatically after the `Retry-After` header (default 60s).
- `404` raises `vibes.errors.NotFound`.
- `403` raises `vibes.errors.Forbidden`.
- Any other non-OK status raises `httpx.HTTPStatusError`.

Pass `raise_for_status=False` to receive the raw response instead.

### Client (WebSocket)

`Client` extends `PassiveClient` with the realtime connection, event listeners and the command
framework.

```python
client = Client(token=TOKEN, prefix="!")
```

- `prefix` is required if you use text commands; it can't be empty or contain spaces.
- `client.user` is a `ClientUser`, available after `on_connect`.
- `client.is_running` tells you whether the socket is open.

| Member | Description |
| --- | --- |
| `start()` | Connect and run forever. |
| `close()` | Disconnect once started (replaces the passive `close()`). |
| `event(name=None)` | Decorator registering an event listener. |
| `subscribe_to(user)` / `unsubscribe_from(user)` | Follow a streamer's events. Requires a running client and a live user. |
| `process_commands(message)` | Parse a `Message` as a command. |
| `sync_commands()` | Push your app commands to VIBES. Call it in `on_connect`. |
| `load_extension(name)` / `unload_extension(name)` | See [Extensions](#extensions). |
| `commands` / `app_commands` | The registered `Command` / `AppCommand` objects. |

## Events

Register listeners with `@client.event()`. The event name is taken from the function name
(`on_connect` → `connected`), or you can pass one explicitly: `@client.event("chat_message")`.

```python
@client.event()
async def on_stream_online(stream: vibes.Stream):
    print(f"{stream.channel} is live: {stream.title}")
```

| Listener | Arguments | Fires when |
| --- | --- | --- |
| `on_connect` | — | The socket is connected and `client.user` is populated. |
| `on_message` | `message: Message` | A chat message is sent. |
| `on_message_delete` | `message: Message` | A *cached* message is deleted. |
| `on_viewer_join` | `stream: Stream, viewer: Viewer` | Someone starts watching a subscribed stream. |
| `on_viewer_leave` | `stream: Stream, viewer: Viewer` | Someone stops watching. |
| `on_new_follower` | `streamer: User, viewer: User` | A streamer you subscribe to gains a follower. |
| `on_stream_like` | `stream: Stream, viewer: Viewer` | Someone likes a stream. |
| `on_stream_online` | `stream: Stream` | A subscribed stream goes live. |
| `on_stream_offline` | `stream: Stream` | A subscribed stream ends. |
| `on_donation` | `donation: Donation` | A donation arrives. |
| `on_command_error` | `error: CommandError \| Exception` | A command fails (see [Error handling](#error-handling)). |

Listeners run as independent asyncio tasks — a slow listener doesn't block the others. Exceptions
raised inside a listener are logged, not propagated.

There is also an internal `_debug` event that receives every raw WebSocket frame:

```python
@client.event()
async def _debug(raw: dict):
    ...
```

## Commands

VIBES supports two kinds of commands. Both accept `role` and `cooldown` options.

### Text commands

Plain chat messages starting with your prefix. You must wire `process_commands` into `on_message`:

```python
from vibes import commands
from vibes.commands import Context

@commands.command()                     # invoked as "!hello Ada"
async def hello(ctx: Context, name: str = "world"):
    await ctx.message.reply(f"Hello, {name}!")

@client.event()
async def on_message(message: vibes.Message):
    if message.author and not message.author.bot and message.content.startswith(client.prefix):
        await client.process_commands(message)
```

`ctx` is always the first parameter and is a `Context`:

| Attribute | Description |
| --- | --- |
| `ctx.message` | The triggering `Message`. Use `await ctx.message.reply(...)` to respond. |
| `ctx.author` | The `Viewer` who sent the message. |
| `ctx.stream` / `ctx.chat` | The `Stream` and its `StreamChat` (`await ctx.chat.send(...)`). |
| `ctx.command` | The `Command` being run. |
| `ctx.client` | The `Client`. |
| `ctx.invocation_id` | The invocation ID (message ID for text commands). |

### Parameters

Parameter types come from annotations. Text commands accept `str`, `int` and `float`; app commands
also accept `Viewer`. A parameter with a default is optional, and when a message contains more words
than the command takes parameters, the leftovers are merged into the last one — so `!hello Ada
Lovelace` passes the full name as a single string, and `!donate 10 Have a good one` passes
`message="Have a good one"`.

```python
@commands.command()
async def donate(ctx: Context, amount: int, message: str = "No message"):
    ...
```

If the user writes something that can't be converted (`!donate abc`), the command is skipped and a
`BadArgument` error is raised.

### Roles

Gate a command behind a minimum role — `Role.VIEWER` (default), `Role.MOD` or `Role.STREAMER`.
Roles are comparable, so the framework checks `ctx.author.role < command.required_role`.

```python
@commands.command(role=vibes.Role.MOD)
async def purge(ctx: Context):
    ...
```

### Cooldowns

`Cooldown(period, max_uses=1, target=Cooldown.VIEWER)` limits how often a command can run.

| Target | Cooldown applies to |
| --- | --- |
| `Cooldown.VIEWER` | One viewer in one stream chat (default). |
| `Cooldown.USER` | One user across all streams. |
| `Cooldown.CHAT` | The entire chat, shared by everybody. |

```python
@commands.command(cooldown=commands.Cooldown(period=10, max_uses=2, target=commands.Cooldown.USER))
async def coinflip(ctx: Context):
    ...
```

### App commands

Native VIBES commands, registered with the API instead of parsed from chat. Use `describe` to give
each option a description shown in the VIBES UI, and put the command description in the docstring.
Call `client.sync_commands()` in `on_connect` to publish them.

```python
@commands.app_command()
@commands.describe(name="Your name", age="Your age")
async def intro(ctx: Context, name: str, age: int):
    """Tells everyone who you are."""
    await ctx.message.reply(f"{ctx.author} is {name}, {age} years old!")
```

App command handlers receive parsed options as **keyword arguments**, and `ctx.invocation_id` is the
invocation ID supplied by the server.

### Error handling

Command errors are never raised out of `process_commands` — they're dispatched to a single
`on_command_error` listener, which receives either a `CommandError` subclass or an unexpected
`Exception` from your callback.

| Error | Extra attributes |
| --- | --- |
| `CommandNotFound` | — |
| `NoPermission` | — |
| `BadArgument` | `.parameter` (`CommandParameter`) |
| `MissingArguments` | — |
| `OnCooldown` | `.cooldown`, `.available_after` (seconds) |

Every `CommandError` carries `.context` (the `Context`).

```python
from vibes.commands import CommandError, BadArgument, MissingArguments, NoPermission, OnCooldown

@client.event()
async def on_command_error(error: CommandError):
    if not isinstance(error, CommandError):
        logging.exception("Unexpected command error", exc_info=error)
        return

    ctx = error.context
    if isinstance(error, BadArgument):
        await ctx.message.reply(f"Invalid value for `{error.parameter.name}`.")
    elif isinstance(error, MissingArguments):
        await ctx.message.reply("Missing required argument(s).")
    elif isinstance(error, NoPermission):
        await ctx.message.reply("You don't have permission to do that.")
    elif isinstance(error, OnCooldown):
        await ctx.message.reply(f"Try again in {error.available_after:.1f}s.")
```

If no `on_command_error` listener is registered, user-input errors are swallowed silently and
unexpected exceptions are logged.

## Extensions

An extension is a module that exposes a `setup(client)` coroutine. Commands and listeners defined
inside it can be removed cleanly at runtime.

`my_extension.py`:

```python
import vibes
from vibes import commands
from vibes.commands import Context
from vibes.ext import Extension, event_listener


class MyExtension(Extension):
    def __init__(self, client):
        self.client: vibes.Client = client

    async def ext_load(self):
        print("Extension loaded")

    async def ext_unload(self):
        print("Extension unloaded")

    @event_listener()                       # events inside an extension use this decorator
    async def on_connect(self):
        print("Connected!")

    @commands.command(role=vibes.Role.MOD)
    async def ping(self, ctx: Context):
        await ctx.message.reply("Pong!")


async def setup(client):                    # the entry point
    await client.add_ext(MyExtension(client))
```

`main.py`:

```python
await client.load_extension("my_extension")   # without ".py"
...
await client.unload_extension("my_extension")
await client.sync_commands()                  # push removed app commands to VIBES
```

The extension class must live in an importable module — it can't be defined in `__main__`.

`load_extension` raises one of `ExtensionNotFound`, `ExtensionAlreadyLoaded`, `NoEntryPointError`
(from `vibes.ext.errors`) or `ExtensionFailed`.

## Models reference

| Type | Key attributes |
| --- | --- |
| `User` | `id`, `username`, `mention`, `avatar_url`, `bio`, `followers`, `created_at`, `url`, `is_live`, `stream`, `premium` |
| `ClientUser` | Everything on `User`, plus `name`, `visibility`, `scopes`, `channels` |
| `Viewer` | Everything on `User`, plus `display_name`, `role`, `bot`, `viewer_id` |
| `Role` | `name`, `level`; predefined as `Role.VIEWER`, `Role.MOD`, `Role.STREAMER` |
| `Stream` | `id`, `title`, `channel`, `category`, `viewers`, `likes`, `mature`, `thumbnail_url`, `url`, `started_at`, `duration`, `chat` |
| `StreamChannel` | `username`, `avatar_url`, `url`, `premium` |
| `StreamCategory` | `slug`, `name` |
| `StreamChat` | `await chat.send(content)` |
| `Message` | `id`, `content`, `author`, `streamer`, `stream`, `reference`, `created_at`, `system`, `await message.reply(content)` |
| `MessageReference` | `id`, `author`, `content` |
| `Donation` | `streamer`, `user`, `amount`, `amount_usd`, `currency`, `message` |
| `Application` | `url`, `key`, `owner`, `rate_limit`, `utm_source`, `mature_allowed`, `webhook` |
| `APIKey` | `name`, `created_at` |
| `ApplicationOwner` | `username`, `url` |
| `ClientWebhook` | `url`, `scope`, `active` |
| `PremiumSubscription` | `name`, `level`; reached via `user.premium` / `channel.premium` |

All datetime attributes (`created_at`, `started_at`) are timezone-aware `datetime.datetime` objects.

`User` and `Viewer` compare by ID, and `str(user)` gives the username.

## Examples

Runnable examples live in [`examples/`](examples/):

| File | Shows |
| --- | --- |
| [`quickstart.py`](examples/quickstart.py) | The smallest useful bot: connect, subscribe, reply. |
| [`events.py`](examples/events.py) | Every event listener and the arguments it receives. |
| [`rest_api.py`](examples/rest_api.py) | `PassiveClient` for REST-only scripts. |
| [`text_commands.py`](examples/text_commands.py) | Text commands, typed parameters, roles and cooldowns. |
| [`app_commands.py`](examples/app_commands.py) | Native app commands, `describe` and `sync_commands`. |
| [`extensions.py`](examples/extensions.py) | Loading and unloading an extension. |
| [`example_extension.py`](examples/example_extension.py) | The extension itself. |

## License

MIT — see [LICENSE](LICENSE).
