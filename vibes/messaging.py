from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .streams import Stream

import datetime
from .users import User, Viewer


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

        self.streamer: User = data.get('streamer')
        self.stream: Stream = data.get('stream')
        self.content: str = data.get('content')

        data['author']['stream'] = self.stream
        self.author: Viewer = Viewer(data['author'], c)
        self.reference: MessageReference | None = MessageReference(data['replyTo']) if data.get('replyTo') else None
        self.type: str = data.get('type')
        self.platform: str = data.get('platform')

        self.created_at: datetime.datetime = datetime.datetime.fromisoformat(
                    data.get('createdAt', '1970-01-01T00:00:00Z').replace("Z", "+00:00")).astimezone()

    async def reply(self, content: str) -> Message:
        """Reply to the message"""



