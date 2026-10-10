from __future__ import annotations
from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .streams import Stream

from .users import User, Viewer

import datetime


class MessageReference:
    "A message referenced by a reply"
    def __init__(self, data: dict):
        self.id: str = data['id']
        self.author: User = data.get('author')
        self.content: str = data.get('content')

class Message:
    "A message sent in a stream chat"
    def __init__(self, data: dict, c):
        self.id: str = data['id']
        self._d: dict = data

        self.streamer: User = data.get('streamer')
        self.stream: Stream = data.get('stream')
        self.content: str = data.get('content')

        self.reference: MessageReference | None = MessageReference(data['replyTo']) if data.get('replyTo') else None
        self.type: str = data.get('type')
        self.platform: str = data.get('platform')

        self.created_at: datetime.datetime = datetime.datetime.fromisoformat(
                    data.get('createdAt', '1970-01-01T00:00:00Z').replace("Z", "+00:00")).astimezone()


    @cached_property
    def author(self) -> Viewer | None:
        """The author of the message. Returns `None` if there's no actual author (in cases of system messages)"""
        return self._d.get('author')

    @property
    def system(self) -> bool:
        """Whether the message is a system message"""
        return self.type == 'system'
    
    async def reply(self, content: str) -> Message:
        """Reply to the message"""



