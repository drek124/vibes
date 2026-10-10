"""## VIBES Extensions System"""


from .listeners import event_listener
from .errors import *



class Extension:
    async def cog_load(self):
        pass