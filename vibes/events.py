from .users import User, Viewer
from .commands import CommandError
from .streams import Stream
from .donations import Donation
from .messaging import Message
from .cache import CACHED_MESSAGES, CACHED_USERS, CACHED_USERS_EXPIRY
# TODO add missing events

ALTERNATIVES = {

    # --- VIBES events ---

    'on_connect': 'connected',
    'on_viewer_join': 'new_viewer',
    'on_viewer_leave': 'viewer_left',
    'on_new_follower': 'new_follower',
    'on_stream_like': 'new_like',
    'on_donation': 'new_donation',
    'on_message': 'chat_message',
    'on_message_delete': 'chat_message_deleted',
    'on_stream_online': 'stream_online',
    'on_stream_offline': 'stream_offline',


    # --- Library events ---

    'on_command_error': 'command_error'

}


async def stream_online_or_offline(client, handlers: list, message: dict):
    data: dict = message['data']['stream']
    stream = Stream(data, client)
    return [
            c(stream) for c in handlers
        ]

async def command_error(client, handlers: list, message: dict):
    e: CommandError = message['error']
    return [
        c(e) for c in handlers
    ]


async def chat_message_deleted(client, handlers: list, message: dict):
    data: dict = message['data']
    msgid = data['id']
    msg: Message = CACHED_MESSAGES.get(msgid)
    if msg is None:
        return [] # If not cached, nothing to give

    # Update streamer to latest version
    _streamer = CACHED_USERS.get(msg.streamer.id, msg.streamer)
    msg.streamer = _streamer if not isinstance(_streamer, dict) else _streamer['obj']
    msg.stream = msg.streamer.stream

    return [
        c(msg) for c in handlers
    ]
    

async def chat_message(client, handlers: list, message: dict):
    data: dict = message['data']
    streamer: User = await client.fetch_user(data['streamerId'])
    data['streamer'] = streamer
    data['stream'] = streamer.stream



    uid = (data.get('user') or {}).get('id')
    if uid:
        author = await client.fetch_user(data['user']['id'], raw=True) or {}
        data['author'] = Viewer(author | data['user'], client)
    

    if data.get('replyTo'):
        rauthor = await client.fetch_user(data['replyTo']['username'])
        data['replyTo']['author'] = rauthor

    obj = Message(data)

    return [
        c(obj) for c in handlers
    ]
    

async def new_donation(client, handlers: list, message: dict):
    data = message['data']
    data['streamer'] = await client.fetch_user(data.get('streamerId'))
    data['viewer'] = await client.fetch_user(data.get('viewerName'))
    donation = Donation(data)
    return [
        c(donation) for c in handlers
    ]

async def new_follower(client, handlers: list, message: dict):

    message = message['data']

    streamer = await client.fetch_user(message.get('streamerId'))
    viewer = await client.fetch_user(message.get('viewerName'))

    return [
        c(streamer, viewer) for c in handlers
    ]


async def new_like(client, handlers: list, message: dict):
    message = message['data']

    streamer = await client.fetch_user(message.get('streamerId'))
    viewer = await client.fetch_user(message.get('viewerName'))

    return [
        c(streamer.stream, viewer) for c in handlers
    ]



async def left_or_new_viewer(client, handlers: list, message: dict):
    message = message['data']
    viewer = message.get('viewerName')
    if viewer:
        viewer = await client.fetch_user(viewer)
    else:
        viewer = User({'is_guest': True}, client)

    streamer = await client.fetch_user(message.get('streamerId'))
    
    return [
            c(streamer.stream, viewer) for c in handlers
        ]

async def debug_websocket(client, handlers: list, message: dict):
    return [
        c(message) for c in handlers
    ]
    