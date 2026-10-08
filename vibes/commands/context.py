
from __future__ import annotations
from typing import TYPE_CHECKING
from ..users import Viewer
from ..messaging import Message
from ..streams import Stream, StreamChat
from . import Command


if TYPE_CHECKING:
    from ..clients import Client


class Context:
    "A text command's context"
    def __init__(self, data: dict):
        self.client: Client = data['client']
        self.message: Message = data['message']
        self.command: Command | None = data.get('command')
        self.author: Viewer = self.message.author
        self.stream: Stream = self.message.stream
        self.chat: StreamChat = self.stream.chat