import json
import traceback
import asyncio
import httpx
import datetime
from torch import Value
import websockets
import logging
from typing import Callable
from .streams import Stream, StreamCategory, StreamChannel
from .users import User, ClientUser
from .cache import CACHED_USERS, CACHED_USERS_EXPIRY
from .messaging import Message
from . import events

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
        c(message["data"]) for c in handlers
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


    "_debug_": events.debug_websocket

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

    async def fetch_user(self, slug: str) -> User | None:
        "Fetch a user by their username, or ID."
        now = datetime.datetime.now()
        slug = slug.lower()
        if slug in CACHED_USERS:
            last: datetime.datetime = CACHED_USERS[slug]['time']
            if (now - last).total_seconds() <= CACHED_USERS_EXPIRY:
                return CACHED_USERS[slug]['obj']
            
        response = await self.client.get(
            'channels/' + slug)
        if response.status_code == 404:
            return None
        
        response.raise_for_status()

        data = response.json()
        obj = User(data.get('data', {}), self)
        CACHED_USERS[obj.id] = CACHED_USERS[obj.username] = {'time': now, 'obj': obj} # Caching to reduce API calls
        return obj
        

class Client(PassiveClient):
    def __init__(self, token, prefix: str = None):
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

    def event(self, event: str = MISSING):
        """Add an event listener.
        ### Example
        ```python
        @client.event()
        async def on_connect():
            print("Logged in successfully!")
        ```"""
        
        def decorator(func: Callable):
            nonlocal event
            if event is MISSING:
                event = func.__name__.lower()
            else:
                event = event.lower()

            event = events.ALTERNATIVES.get(event) or event
            if event not in self._event_handlers:
                self._event_handlers[event] = []

            handlers = self._event_handlers[event]
            if func in handlers:
                raise ValueError("Event listener is already listening to this event")
            
            handlers.append(func)

            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
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
                await self.client.aclose()
                heartbeat_task.cancel()
                await asyncio.gather(heartbeat_task, return_exceptions=True)
            
            self.close = _close
            heartbeat_task = asyncio.create_task(_send_heartbeat(ws))

            async for message in ws:
                try:
                    data: dict = json.loads(message)
                    event_type = data.get('type')
                    to_call = []



                    if event_type == 'reconnect':
                        _data = data['data']
                        reason = _data.get('reason', 'Unknown reason')
                        logging.info(f"Reconnect requested by server; Reason: \"{reason}\". Reconnecting...")
                        await self._reconnect()

                    

                    await self._trigevent(type=event_type, data=data)

                    


                except json.JSONDecodeError:
                    logging.warning("Failed to parse non-JSON message:" + str(message))


    async def _trigevent(self, **kwargs):
        event_type: str = kwargs['type']
        data: dict = kwargs['data']

        if event_type in self._event_handlers:
            handler = EVENT_HANDLERS.get(event_type, _default_event_handler)
            to_call: list = await handler(self, self._event_handlers[event_type], data)



        if '_debug_' in self._event_handlers:
            to_call += await events.debug_websocket(self, self._event_handlers['_debug_'], data)
            
        if to_call:
            r = await asyncio.gather(*to_call, return_exceptions=True)
            for res in r:
                if isinstance(res, BaseException):
                    tb_str = "".join(
                        traceback.format_exception(type(res), res, res.__traceback__)
                    )
                    logging.error(f"Error occurred in background task:\n{tb_str}")
                    

    async def process_commands(message: Message):
        """Process a text command.
        The client does checks to validate user input
        """