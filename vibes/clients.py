import json
import traceback
import asyncio
from types import CoroutineType
import httpx
import datetime
import websockets
import logging
import sys
import importlib
from typing import Callable, Coroutine
from .streams import Stream, StreamCategory, StreamChannel
from .users import User, ClientUser
from .cache import CACHED_USERS, CACHED_USERS_EXPIRY
from .messaging import Message
from . import events

from .ext import Extension
from .ext.errors import (
    ExtensionAlreadyLoaded,
    ExtensionFailed,
    ExtensionNotFound,
    NoEntryPointError,
)
from .ext.listeners import _add_event_listener
from .ext.listeners import _LISTENERS as _EXT_LISTENERS

from .commands import (
    CommandError, 
    NoPermission, 
    BadArgument, 
    MissingArguments, 
    CommandNotFound, 
    OnCooldown,
    Command,
    Context,
    _COMMANDS,
    _EXT_COMMANDS,
    _COMMAND_USES,
    command,
    Cooldown
    
)

BASE_URL = 'https://backend.vibes.stream/api/v1/'
WEBSOCKET_URL = 'wss://backend.vibes.stream/api/ws'
MISSING = object()

# TODO:
# Add a function to raise Forbidden, NotFound, etc, which would also handle rate limits
# if res.status_code == 429:
#    wait = int(res.headers.get("Retry-After", 60))

async def _default_event_handler(client, handlers: list, message: dict):
    return [
        c() for c in handlers
    ]
        
async def _error_event_handler(client, handlers: list, message: dict):
    logging.warning(f"Server sent an error:\n \"{message["data"]["message"]}\"")

    return [
        c(message) for c in handlers
    ]

EVENT_HANDLERS = {
    "new_viewer": events.left_or_new_viewer,
    "viewer_left": events.left_or_new_viewer,
    "new_follower": events.new_follower,
    "new_like": events.new_like,
    "new_donation": events.new_donation,
    "error": _error_event_handler,
    "chat_message": events.chat_message,
    'chat_message_deleted': events.chat_message_deleted,

    "command_error": events.command_error,
    "_debug": events.debug_websocket

}


async def _send_heartbeat(websocket):
    """Sends a heartbeat every 30 seconds to keep the connection alive"""
    try:
        while True:
            await asyncio.sleep(30)
            heartbeat_payload = json.dumps({"type": "heartbeat"})
            await websocket.send(heartbeat_payload)
    except asyncio.CancelledError:
        pass  # when the task is canceled upon disconnect


class ApplicationOwner:
    def __init__(self, data: dict):
        self.username: str = data.get('username')
        self.url: str = data.get('url')

    def __str__(self):
        return self.username

class ClientWebhook:
    def __init__(self, data: dict):
        self.url: str = data.get('url')
        self.scope: str = data.get('scope')
        self.active: bool = data.get('active')


class APIKey:
    def __init__(self, data: dict):
        self.name: str = data.get('name')
        self.created_at: datetime.datetime = datetime.datetime.fromisoformat(
            data.get('createdAt', '1970-01-01T00:00:00Z').replace("Z", "+00:00")).astimezone()

class Application:
    def __init__(self, data: dict):
        self.url: str = data.get('url')
        self.key = APIKey(data.get('key', {}))
        self.owner = ApplicationOwner(data.get('owner', {}))
        self.rate_limit: dict = data.get('rateLimit')
        self.utm_source: str = data.get('utmSource')
        self.mature_allowed: bool = data.get('matureAllowed')
        webhook = data.get('webhook')
        self.webhook: ClientWebhook | None = ClientWebhook(webhook) if webhook else None


class PassiveClient:
    def __init__(self, token: str):
        """## VIBES Passive Client
        This passsive client is purely used for API calls.

        ### Parameters 
        - token: Your app's token. Don't include `Bearer`. Get it [here](https://vibes.stream/dashboard/plugins/api).
        """
        self.client = httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}, base_url=BASE_URL)

    async def close(self):
        """Close the client"""
        await self.client.aclose()

    async def fetch_client(self) -> Application:
        """Fetch your application"""
        response = await self.client.get('me')
        response.raise_for_status()

        return Application(response.json().get('data', {}))

    async def fetch_streams(self, *, limit: int = 100, category: str | StreamCategory = None, mature: bool = True) -> list[Stream]:
        """Get the current streams on VIBES.
        ## Parameters
        - limit: The limit of the streams pulled. Max is 100.
        - category: The slug of the category to fetch the streams from. (e.g. `'chit-chat'`)
        - mature: Include 18+ streams. If client account is not 18+, server will return `403 Forbidden`
        """
        if limit <= 0:
            raise ValueError("Limit cannot be lower than 1")


        body = {'limit': limit}
        if category:
            if isinstance(category, StreamCategory):
                body['category'] = category.slug
            else:
                body['category'] = category.lower().replace(' ', '-')
        if mature:
            body['mature'] = 'include'

        response = await self.client.get(
            'streams/live',
            params=body)

        response.raise_for_status()

        data = response.json()
        
        return [Stream(i, self) for i in data.get('data', [])]

    async def fetch_user(self, slug: str, **kwargs) -> User | None:
        "Fetch a user by their username, or ID."
        now = datetime.datetime.now()
        slug = slug.lower()
        if slug in CACHED_USERS:
            last: datetime.datetime = CACHED_USERS[slug]['time']
            if (now - last).total_seconds() <= CACHED_USERS_EXPIRY:
                return CACHED_USERS[slug]['obj' if not kwargs.get('raw') else 'raw']
            
        response = await self.client.get(
            'channels/' + slug)
        if response.status_code == 404:
            return None
        
        response.raise_for_status()

        data = response.json()
        if kwargs.get('raw'):
            return data
        obj = User(data.get('data', {}), self)
        CACHED_USERS[obj.id] = CACHED_USERS[obj.username] = {'time': now, 'obj': obj, 'raw': data} # Caching to reduce API calls
        return obj
        

class Client(PassiveClient):
    def __init__(self, token, *, prefix: str = None):
        """## VIBES Client
        Initialize a WebSocket client to VIBES. Make sure to call `.start()` to establish the connection.
        ### Parameters 
        - token: Your app's token. Don't include `Bearer`. Get it [here](https://vibes.stream/developers/applications).
        - prefix: The command prefix. Required if you're going to use text commands.

        ### How to process a command?
        ```python
        @client.event()
        async def on_message(message: Message):
            if message.author.bot:
                return # Ignore bots
            if message.content.startswith('!'): # Or whatever prefix you entered
                await client.process_commands(message) # The bot automatically processes & calls the command
                return
        ```
        It's important to know that the bot does checks to make sure all the parameters entered by the user are valid and good to go,
        otherwise, it'd raise a swallowed command error.
        """
        self._token = token
        super().__init__(token)
        self._extensions = {}
        self._event_handlers: dict = {
            "error": []
        }
        if prefix is not None:
            if prefix == '':
                raise ValueError("Prefix can't be empty")
            if ' ' in prefix:
                raise ValueError("Spaces aren't allowed in prefix.")
                
        self.prefix: str = prefix
        self._ws: websockets.ClientConnection = None
        self.user: ClientUser = None


    @property
    def commands(self) -> list[Command]:
        """The client's text commands"""
        return _COMMANDS

    @property
    def is_running(self) -> bool:
        return self._ws is not None

    @property
    def _all_event_listeners(self) -> dict:
        # All event listeners, global & in extensions.
        combined = {}
        dicts = ([dict(d) for d in _EXT_LISTENERS.values()] if _EXT_LISTENERS else []) + [self._event_handlers]
        for d in dicts:
            for key, value in d.items():
                if key not in combined:
                    combined[key] = []
                for listener in value:
                    combined[key].append(listener)
        return combined

    async def subscribe_to(self, user: User | StreamChannel):
        """Subscribe to a user's stream events"""
        if not self._ws:
            raise ValueError("Client isn't running")
        if not getattr(user, 'stream', True):
            raise ValueError("User isn't streaming")
        
        await self._ws.send(json.dumps({'type':'subscribe', 'data': {'username': user.username}}))

    async def unsubscribe_from(self, user: User | StreamChannel):
        """Unsubscribe from a user's stream events"""
        if not self._ws:
            raise ValueError("Client isn't running")
        await self._ws.send(json.dumps({'type':'unsubscribe', 'data': {'username': user.username}}))


    async def add_ext(self, extension: Extension):
        """Add an extension to the client"""

        if not isinstance(extension, Extension):
            raise TypeError("Extensions must be of the \"Extension\" type; use like \"class MyExt(Extension)\"")

        ext_name = type(extension).__module__      
        if ext_name == '__main__':
            raise ValueError("Extensions can't be in the main file")
        
        if ext_name not in self._extensions:
            raise ExtensionNotFound(ext_name)

        for name in dir(extension):
            method = getattr(extension, name)
            if getattr(method, "_is_event_listener", False):

                event_name = method._event_name
                _EXT_LISTENERS.setdefault(ext_name, {}).setdefault(event_name, []).append(method)
            
            if getattr(method, "_is_command", False):
                args: dict = method._command_args | {'ext': ext_name}
                command(**args)(method)


       
        self._extensions[ext_name]['obj'] = extension
        await extension.ext_load()



    async def load_extension(self, name: str, package: str = None) -> None:
        """
        Loads an extension.

        An extension is a python module that contains commands and/or
        listeners.

        An extension must have a global async function `setup` defined as
        the entry point on what to do when the extension is loaded.

        
        ### Example
        ```python
        class MyExtension():
            ...
        async def setup(client):
            await client.add_ext(MyExtension(client))
            print("Extension loaded")
        ```

        ### Parameters
        - name:
            The extension name to load. It must be dot separated like
            regular Python imports if it's a sub-module. (e.g.
            `ext.test` if you want to import `ext/test.py`).
        - package:
            The package name to resolve relative imports with.
            This is required when loading an extension using a relative path, e.g `.pac.test`.


        ### Raises
        ExtensionNotFound
            The extension could not be imported because it wasn't found/resolved.
        ExtensionAlreadyLoaded
            The extension is already loaded.
        NoEntryPointError
            The extension doesn't have the `setup` function.
        ExtensionFailed
            The extension or its `setup` had an execution error.
    
            
        _*inspired by [discord.py](https://github.com/Rapptz/discord.py/) 💙*_ 
        """

        try: # Resolving the name
            name = importlib.util.resolve_name(name, package)
        except ImportError:
            raise ExtensionNotFound(name)

        if name in self._extensions:
            raise ExtensionAlreadyLoaded(name)

        spec = importlib.util.find_spec(name)
        if spec is None:
            raise ExtensionNotFound(name)

        await self._load_from_module_spec(spec, name)

    async def _load_from_module_spec(self, spec: importlib.machinery.ModuleSpec, key: str) -> None:
        lib = importlib.util.module_from_spec(spec)
        sys.modules[key] = lib
        try:
            spec.loader.exec_module(lib)  
        except Exception as e:
            del sys.modules[key]
            raise ExtensionFailed(key, e) from e

        try:
            setup = getattr(lib, 'setup')
        except AttributeError:
            del sys.modules[key]
            raise NoEntryPointError(key)
                

        try:
            self._extensions[key] = {'lib': lib}
            await setup(self)

        except Exception as e: 
            await self._remove_ext(key)
            raise ExtensionFailed(key, e) from e

    async def unload_extension(self, name: str, package: str = None):
        """
        Unloads an extension.
        
        When an extension is unloaded, all its commands & event listeners will be removed.
        ### Parameters
        - name:
            The extension name to load. It must be dot separated like
            regular Python imports if it's a sub-module. (e.g.
            `ext.test` if you want to import `ext/test.py`).
        - package:
            The package name to resolve relative imports with.
            This is required when loading an extension using a relative path, e.g `.pac.test`.

        ### Raises
        - ExtensionNotFound: If the extension wasn't found, or isn't loaded.
        """


        try: # Resolving the name
            name = importlib.util.resolve_name(name, package)
        except ImportError:
            raise ExtensionNotFound("Not found:" + name)

        if name not in self._extensions:
            raise ExtensionNotFound("Not loaded:" + name)
        await self._remove_ext(name)

    async def _remove_ext(self, name: str):
        # Unload from the client
        obj: Extension = self._extensions[name].get('obj')
        if obj:

            await obj.ext_unload()

        self._extensions.pop(name, None)
        sys.modules.pop(name, None)
        
        cmds = _EXT_COMMANDS.get(name, [])

        for cmd in cmds:
            _COMMANDS.remove(cmd)

        if cmds:
            _EXT_COMMANDS.pop(name)

        if name in _EXT_LISTENERS:
            _EXT_LISTENERS.pop(name)


    def event(self, event: str = None):
        """Add an event listener.
        ### Parameters
        - event: The name of the event. If `None`, the name of the callback will be taken instead.
        ### Example
        ```python
        @client.event()
        async def on_connect():
            print("Logged in successfully!")
        ```"""
        
        def decorator(func: Callable):
            nonlocal event
            _add_event_listener(event, self._event_handlers, func)

            return func
        return decorator


    async def _reconnect(self):
        await self._ws.close()
        await self.start()

    async def start(self):
        """Start the connection to VIBES"""

        uri = WEBSOCKET_URL + '?apiKey=' + self._token

        logging.info('Establishing a connection to VIBES...')

        res = await self.client.get("app")
        res.raise_for_status()
        self.user = ClientUser(res.json()['data'], self)
        

        

        async with websockets.connect(uri) as ws:
            logging.info("Connected to VIBES successfully.")
            self._ws = ws
            async def _close():
                self._ws = None
                await ws.close()
                heartbeat_task.cancel()
                await asyncio.gather(heartbeat_task, return_exceptions=True)
            
            self.close = _close
            heartbeat_task = asyncio.create_task(_send_heartbeat(ws))

            async for message in ws:
                try:
                    data: dict = json.loads(message)
                    logging.info(message)
                    event_type = data.get('type')

                    
                    if event_type == 'reconnect':
                        _data = data['data']
                        reason = _data.get('reason', 'Unknown reason')
                        logging.info(f"Reconnect requested by server; Reason: \"{reason}\". Reconnecting...")
                        await self._reconnect()

                    try:

                        await self._trigevent(type=event_type, data=data)

                    except Exception as e:
                        tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                        logging.critical(f"Error occurred in preparation of background task:\n{tb_str}")

                except json.JSONDecodeError:
                    logging.warning("Failed to parse non-JSON message:" + str(message))


    async def _trigevent(self, **kwargs):
        event_type: str = kwargs['type']
        data: dict = kwargs['data']


        listeners = self._all_event_listeners
        if event_type in listeners:
            handler = EVENT_HANDLERS.get(event_type, _default_event_handler)
            to_call: list = await handler(self, listeners[event_type], data)
        else:
            to_call = []


        if '_debug' in listeners:
            to_call += await events.debug_websocket(self, listeners['_debug'], data)
            
        if to_call:
            r = await asyncio.gather(*to_call, return_exceptions=True)
            for res in r:
                if isinstance(res, BaseException):
                    tb_str = "".join(
                        traceback.format_exception(type(res), res, res.__traceback__)
                    )
                    logging.error(f"Error occurred in background task:\n{tb_str}")
                    

    async def process_commands(self, message: Message):
        """Process a text command.
        The client does checks to validate user input; use `on_command_error(error: CommandError | Exception)` event listener to follow-up & send feedback.
        """
        try:
            if self.prefix is None:
                raise NotImplementedError("Can't process a command without a command prefix present")
            
            if not message.content.startswith(self.prefix):
                return
            
            content = message.content[len(self.prefix):].split(' ')
            command: Command = next((c for c in _COMMANDS if c.name == content[0]), None)
            ctx = {
                'message': message,
                'client': self
            }

            if command is None:
                raise CommandNotFound(ctx=Context(ctx)) 
            ctx['command'] = command
            context = Context(ctx)
            content.remove(content[0])

            if message.author.role < command.required_role:
                raise NoPermission(ctx=context)

            params = command.parameters
            if len(content) < len([p for p in params if p.required]):
                raise MissingArguments(ctx=context)

            _to_pass = [context]

            if params:
                diff = len(content) - len(params)
                if diff > 0: # If split is out of range of the command params
                    _reserve = []
                    for ii, item in enumerate(content.copy(), 1):
                        if ii <= len(content) - diff:
                            _reserve.append(item)
                            content.remove(item)
                    content = _reserve + [' '.join(content)]


                for ii, item in enumerate(content):
                    try:
                        param = params[ii]
                        conversion = await param._process(item)
                        _to_pass.append(conversion)

                    except (ValueError):
                        raise BadArgument(ctx=context, badarg=param)



            # Cooldown Handling
            cd = command.cooldown
            if cd:
                if cd.target == Cooldown.VIEWER:
                    tid = context.author.viewer_id
                elif cd.target == Cooldown.USER:
                    tid = context.author.id
                elif cd.target == Cooldown.CHAT:
                    tid = context.stream.id

                all_uses = _COMMAND_USES.setdefault(tid, {})
                uses = all_uses.setdefault(command.name, {})

                times = uses.get('uses', 0)
                last_use = uses.get('last_use', datetime.datetime.fromtimestamp(0))
                now = datetime.datetime.now()

                if times > 0:
                    diff = (now - last_use).total_seconds()
                    if diff > cd.period:
                        times = 0
                        uses['last_use'] = now
                    elif times >= cd.max_uses:
                        raise OnCooldown(ctx=context, cd=cd,
                                        available_after=cd.period - diff)
                else:
                    uses['last_use'] = now

                uses['uses'] = times + 1
                

            await command.callback(*_to_pass)
        except CommandError as e:
            # If there are no on_command_error listeners, swallow user-input related exceptions B)
            await self._trigevent(type='command_error', data={'error': e})
            
        except Exception as e:
            # Logic exceptions need to be shown to the developer
            if 'command_error' in self._all_event_listeners:
                await self._trigevent(type='command_error', data={'error': e})
                return
            
            tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            logging.error(f"Error occurred in command execution:\n{tb_str}")
