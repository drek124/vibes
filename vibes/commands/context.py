
from __future__ import annotations
from typing import TYPE_CHECKING
from ..users import Viewer
from ..messaging import Message
from ..streams import Stream, StreamChat


if TYPE_CHECKING:
    from ..clients import Client
    from . import Command, AppCommand



_COMMANDS: list[Command] = []
_COMMAND_USES: dict[Viewer, dict] = {}
_APP_COMMANDS: list[AppCommand] = []
_EXT_COMMANDS: dict[str, list[Command, AppCommand]] = {}


class Context:
    "A text command's context"
    def __init__(self, data: dict):
        self._d: dict = dict
        self.client: Client = data['client']
        self.message: Message = data['message']
        self.command: Command | AppCommand | None = data.get('command')
        self.author: Viewer = self.message.author
        self.stream: Stream = self.message.stream
        self.chat: StreamChat = self.stream.chat

    @property
    def invocation_id(self) -> str | None:
        """The ID of the command invocation."""
        return self._d.get('invocation_id', getattr(self.message, 'id', None))