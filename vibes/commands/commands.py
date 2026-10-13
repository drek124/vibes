

import inspect
import types
from inspect import Parameter
from typing import get_args, get_origin, Union
from typing import Callable

from .params import _ALLOWED_CLASSES
from ..users import Role, Viewer
from .cooldown import Cooldown
from .context import _COMMANDS, _EXT_COMMANDS

MISSING = object()

_UNION_ORIGINS = (Union, types.UnionType)

class Command:
    """A VIBES chat command."""
    def __init__(self, **data):
        self.name: str = data['name']
        self._slug: str = self.name
        self.callback = data['callback']
        self.required_role: Role = data['required_role']
        self.parameters: list[CommandParameter] = data['params']
        self.cooldown: Cooldown | None = data['cooldown']


    async def callback(self, *args):
        # i mean its impossible for this error to be raised lol
        raise NotImplementedError("No callback has been implemented for this command")

    def __str__(self):
        return self.name




class CommandParameter:
    def __init__(self, **data):
        self.name: str = data['name']
        self.required: bool = data['required']
        self._type = data['type']

        self._process = data['paramclasses'][self._type]

    async def _process(self, *args, **kwargs):
        raise NotImplementedError() # This can't be raised anyway



def command(name: str = MISSING, *, role: Role = Role.VIEWER, cooldown: Cooldown = None, **kwargs):
    """Create a new text command.
    - name: The name of the command; if missing, the name of the callback will be used instead
    - role: The minimum required role that can access this command. The available roles:
       - `Role.VIEWER`
       - `Role.MOD`
       - `Role.STREAMER`
    - cooldown: The cooldown rule of the command
    ### Example
    ```python

    @commands.command()
    async def hello(ctx, name: str): # "name" is a string parameter typed out by the user
        await ctx.reply(f"Hello, {name}! You have {ctx.user.followers} followers!")

    @commands.command(role=Role.MOD) # Only moderators & higher can access
    async def ping(ctx): # Must have the first parameter reserved for context
        await ctx.reply("Pong!")
    ```"""

    def decorator(func: Callable):
        nonlocal name, role
        if name is MISSING:
            name = func.__name__.lower()
        else:
            name = name.lower()

        qname = func.__qualname__
        if '.' in qname and not kwargs.get('ext'): # If in an unloaded extension
            func._is_command = True
            func._command_args = {'name': name, 'role': role, 'cooldown': cooldown} | kwargs
            return func

        for command in _COMMANDS:
            if command.name == name:
                raise ValueError(f"The text command \"{name}\" already exists.")

        params: dict = inspect.signature(func).parameters

        processed_params: list[CommandParameter] = []

        for i, _p in enumerate(params.items()):
            pname, param = _p 
            if i == 0: # Ignore the "ctx" param
                continue

            if param.kind not in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY):
                raise ValueError("A command callback can't process \"*args\", \"*kwargs\" or non-positional parameters")

            
            ptype = param.annotation

            if ptype is Parameter.empty:  
                ptype = str

            else:

                origin = get_origin(ptype)
                if origin in _UNION_ORIGINS:
                    types_list = get_args(ptype)

                    ptype = types_list[0] 

                inner_origin = get_origin(ptype)
                if inner_origin is not None:
                    ptype = inner_origin

                if ptype not in _ALLOWED_CLASSES:
                    raise ValueError(f"Parameter type \"{ptype}\" for \"{pname}\" can't be proccessed")
            
            required: bool = param.default is Parameter.empty

            processed_params.append(
                CommandParameter(
                    name=pname,
                    type=ptype,
                    required=required,
                    paramclasses=_ALLOWED_CLASSES
                )
            )

        obj = Command(name=name, callback=func, required_role=role, cooldown=cooldown, params=processed_params)
        _COMMANDS.append(obj)

        # Detect if its in an extension; this way we can remove them if we decide to unload an extension
        if '.' in qname:
            _ext = kwargs['ext']
            if _ext not in _EXT_COMMANDS:
                _EXT_COMMANDS[_ext] = []

            _EXT_COMMANDS[_ext].append(obj)

        return func
    
    return decorator



