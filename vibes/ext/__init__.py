"""## VIBES Extensions System"""


from .listeners import event_listener
from .errors import *



class Extension:
    async def ext_load(self):
        """The callback that's called when the extension is loaded"""
        pass

    async def ext_unload(self):
        """The callback that's called when the extension has been unloaded"""
        pass