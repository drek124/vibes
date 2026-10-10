"""## VIBES Chat Commands system
***NOTE:** This module relies on chat messages as commands, not the native VIBES commands feature.*
"""

from .commands import command, CommandParameter, Command, _COMMANDS, _EXT_COMMANDS
from .context import Context
from .errors import *
from . import errors
from .params import _ALLOWED_CLASSES
