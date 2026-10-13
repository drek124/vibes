"""## VIBES Chat Commands system
***NOTE:** This module relies on chat messages as commands, not the native VIBES commands feature.*
"""

import datetime

from .commands import command, CommandParameter, Command
from .app_commands import app_command, AppCommand, describe
from .context import Context, _COMMANDS, _EXT_COMMANDS, _COMMAND_USES, _APP_COMMANDS
from .errors import *
from . import errors
from .params import _ALLOWED_CLASSES
from .cooldown import Cooldown

__all__ = [
    "command", "CommandParameter", "Command",
    "app_command", "AppCommand", "Context", 
    "errors", "Cooldown", "describe"
    ] + [name for name in dir(errors)]

async def _process_command_cooldown(cmd: Command | AppCommand, context: Context):
    cd = cmd.cooldown
    if cd:
        if cd.target == Cooldown.VIEWER:
            tid = context.author.viewer_id
        elif cd.target == Cooldown.USER:
            tid = context.author.id
        elif cd.target == Cooldown.CHAT:
            tid = context.stream.id

        all_uses = _COMMAND_USES.setdefault(tid, {})
        uses = all_uses.setdefault(cmd._slug, {})

        times = uses.get('uses', 0)
        last_use = uses.get('last_use', datetime.datetime.fromtimestamp(0))
        now = datetime.datetime.now()

        if times > 0:
            diff = (now - last_use).total_seconds()
            if diff > cd.period:
                times = 0
                uses['last_use'] = now
            elif times >= cd.max_uses:
                raise OnCooldown(ctx=context, cd=cd,
                                available_after=cd.period - diff)
        else:
            uses['last_use'] = now

        uses['uses'] = times + 1