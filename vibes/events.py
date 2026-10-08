from .users import User
from .streams import Stream
from .donations import Donation
from .messaging import Message
from .cache import CACHED_MESSAGES, CACHED_USERS, CACHED_USERS_EXPIRY

ALTERNATIVES = {
    'on_connect': 'connected',
    'on_viewer_join': 'new_viewer',
    'on_viewer_leave': 'viewer_left',
    'on_new_follower': 'new_follower',
    'on_stream_like': 'new_like',
    'on_donation': 'new_donation',
    'on_message': 'chat_message',
    'on_message_delete': 'chat_message_deleted'

}




async def chat_message_deleted(client, handlers: list, message: dict):
    data: dict = message['data']
    msgid = data['id']
    msg: Message = CACHED_MESSAGES.get(msgid)
    if msg is None:
        return [] # If not cached, nothing to give

    # Update streamer to latest version
    msg.streamer = CACHED_USERS.get(msg.streamer.id, msg.streamer)
    msg.stream = msg.streamer.stream

    return [
        c(msg) for c in handlers
    ]
    

async def chat_message(client, handlers: list, message: dict):
    data: dict = message['data']
    streamer: User = await client.fetch_user(data['streamerId'])
    data['streamer'] = streamer
    data['stream'] = streamer.stream
    data['author'] = await client.fetch_user(data['user']['id'])

    if data.get('replyTo'):
        rauthor = await client.fetch_user(data['replyTo']['username'])
        data['replyTo']['author'] = rauthor

    obj = Message(data, client)

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
    