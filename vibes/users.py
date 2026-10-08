

import datetime
from typing import Literal

from .models import PremiumSubscription
from .streams import Stream


ROLE_LEVELS = {
    'viewer': 1,
    'moderator': 10,
    'streamer': 20
}


class User:
    def __init__(self, data: dict, c):
        self.guest: bool = data.get('is_guest', False)
        self.id: str = data['id'] if not self.guest else None # Strict on id i guess
        self.username: str = data.get('username')
        self.avatar_url: str = data.get('avatarUrl')
        self.bio: str = data.get('bio')
        self.followers: int = data.get('followers', 0)

        self.created_at = datetime.datetime.fromisoformat(
                    data.get('createdAt', '1970-01-01T00:00:00Z').replace("Z", "+00:00")).astimezone()

        self.url: str = data.get('url')
        stream = data.get('stream')
        self.is_live: bool = data.get('isLive', False)
        self.stream: Stream | None = Stream(stream, c) if stream else None
        self.premium = PremiumSubscription(data.get('premium') or {})

    def __str__(self):
        return self.username

    def __eq__(self, other):
        
        if type(other) not in [User, Viewer, ClientUser]:
            return False
        
        return other.id == self.id
        

class ClientUser(User):
    def __init__(self, data, c):
        super().__init__(data, c)
        self.username: str = data.get('slug')
        self.name: str = data.get('name')
        self.visibility: Literal['private', 'public'] = data.get('visibility')
        self.scopes: list[str] = data.get('scopes')
        self.channels: list[str] = [i['username'] for i in data.get('channels', [])]  


class Viewer(User):
    def __init__(self, data: dict, c):
        super().__init__(data, c)

        self.display_name: str = data.get('displayName')
        self.avatar_url: str = data.get('avatarUrl')
        role = data.get('role', 'viewer')
        self.role: Literal['viewer', 'moderator', 'streamer'] = data.get('role') 
        self.bot: bool = data.get('bot')


class Role:

    VIEWER: Role = ...
    MOD: Role = ...
    STREAMER: Role = ...

    def __init__(self, data: dict):
        self.name: str = data['name']
        self.level: int = ROLE_LEVELS.get(self.name, 0)

Role.VIEWER = Role({'name': 'viewer'})
Role.MOD = Role({'name': 'moderator'})
Role.STREAMER = Role({'name': 'streamer'})

