from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .messaging import Message
import datetime
from .models import PremiumSubscription

class StreamCategory:
    def __init__(self, data: dict):
        self.slug: str = data.get('slug')
        self.name: str = data.get('name')

class StreamChannel:
    def __init__(self, data: dict):
        self.username: str = data.get('username')
        self.avatar_url: str = data.get('avatarUrl')
        self.url: str = data.get('url')
        self.premium = PremiumSubscription(data.get('premium') or {})
        
    def __str__(self):
        return self.username

class Stream:
    def __init__(self, data: dict, c):
        self._client = c
        self.id: str = data.get('streamId') or data.get('id')
        self.title: str = data.get('title')
        self.started_at = datetime.datetime.fromisoformat(
            data.get('startedAt', '1970-01-01T00:00:00Z').replace("Z", "+00:00")).astimezone()
        
        self.viewers: int = data.get('viewers', 0)
        self.likes: int = data.get('likes', 0)
        self.mature: bool = data.get('mature')
        self.category = StreamCategory(data.get('category') or {})
        self.thumbnail_url: str = data.get('thumbnailUrl')
        self.url: str = data.get('url')
        self.channel = StreamChannel(data.get('channel') or {})
        self.chat = StreamChat(self)

    @property
    def duration(self) -> float:
        "The amount of seconds the stream has been running for"
        return (datetime.datetime.now(self.started_at.tzinfo) - self.started_at).total_seconds()
    
class StreamChat:
    def __init__(self, stream):
        self.stream: Stream = stream

    async def send(self, content: str) -> Message:
        """Send a text message in the stream chat."""
        response = await self.stream._client.send_request(
            self.stream._client.client.post,
            f'channels/{self.stream.channel.username}/messages',
            json={'content': content})

        data = response.json()

        data['stream'] = self.stream



        return Message(data)

