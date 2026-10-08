
from .. import Viewer, Message, Stream, StreamChat
from . import Command




class Context:
    "A text command's context"
    def __init__(self, data: dict):
        self.message: Message = data['message']
        self.command: Command = data['command']
        self.author: Viewer = self.message.author
        self.stream: Stream = self.message.stream
        self.chat: StreamChat = self.stream.chat