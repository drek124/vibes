from .commands import CommandParameter
from .context import Context
from .. import Role
import drekord

class CommandError(Exception):
    """
    Universal Command Error class.
    Use `on_command_error(error: CommandError)` event listener
    """
    def __init__(self, *args, ctx):
        self.context: Context = ctx
        super().__init__(*args)


class NoPermission(CommandError):
    "The exception raised when user has no permissions to run a command"
    def __init__(self, *args, ctx):
        super().__init__(*args, ctx=ctx)

class BadArgument(CommandError):
    """The exception raised when a user writes an invalid argument type
    ### Example
    - Command: `donate(amount: int)`
      - Bad user input: `!donate abc` <-- 🚫 `"abc"` cannot be converted to `int`
      - Good user input `!donate 10` <-- ✅ `"10"` converted to `10`
    """
    def __init__(self, *args, ctx, badarg):
        self.parameter: CommandParameter = badarg
        super().__init__(*args, ctx=ctx)

class MissingArguments(CommandError):
    """The exception raised when a user leaves out required arguments
    ### Example
    - Command: `donate(amount: int, message: str = "No message")`
      - Bad user input: `!donate` <-- 🚫 `amount` is required
      - Good user input `!donate 10` <-- ✅ `amount` is present, `message` is optional
      - Good user input `!donate 10 Have a good day!` <-- ✅ All required & optional arguments present
    """
    def __init__(self, *args, ctx,):
        super().__init__(*args, ctx=ctx)


class CommandNotFound(CommandError):
    def __init__(self, *args, ctx):
        super().__init__(*args, ctx=ctx)


__all__ = [
    "CommandError",
    "NoPermission",
    "BadArgument",
    "MissingArguments",
    "CommandNotFound"
]