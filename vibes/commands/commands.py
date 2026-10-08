

import inspect
import types
from inspect import Parameter
from typing import get_args, get_origin, Union

from .params import _ALLOWED_CLASSES
from ..users import Role
from typing import Callable


MISSING = object()

_UNION_ORIGINS = (Union, types.UnionType)

class Command:
    """A VIBES chat command."""
    def __init__(self, **data):
        
        self.name: str = data['name']
        self.callback = data['callback']
        self.required_role: Role = data['required_role']
        self.parameters: list[CommandParameter] = data['params']


    async def callback(self, *args):
        raise NotImplementedError("No callback has been implemented for this command")

    def __str__(self):
        return self.name

_COMMANDS: list[Command] = []

class CommandParameter:
    def __init__(self, **data):
        self.name: str = data['name']
        self.required: bool = data['required']
        self._type = data['type']

        self._process = _ALLOWED_CLASSES[self._type]

    async def _process(self, text: str):
        raise NotImplementedError() # This shouldn't be raised anyway



def command(name: str = MISSING, *, role: Role = Role.VIEWER):
    """Create a new text command.
    - name: The name of the command; if missing, the name of the callback will be used instead
    - role: The minimum required role that can access this command.
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


        for command in _COMMANDS:
            if command.name == name:
                raise ValueError(f"The command \"{name}\" already exists.")

        params: dict = inspect.signature(func).parameters

        processed_params: list[CommandParameter] = []

        for i, pname, param in enumerate(params.items()):

            if i == 0: # Ignore the "ctx" param
                continue

            if param.kind not  in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD):
                raise ValueError("A command callback can't process \"*args\" or \"*kwargs\" parameters")

            if param.kind is Parameter.KEYWORD_ONLY:
                raise ValueError("A command callback musn't have non-positional arguments.")


            
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
                    raise ValueError(f"Unknown parameter type \"{ptype}\" for \"{pname}\"")
            
            required: bool = param.default is Parameter.empty

            processed_params.append(
                CommandParameter(
                    name=pname,
                    type=ptype,
                    required=required
                )
            )


        _COMMANDS.append(Command(name=name, callback=func, required_role=role, params=processed_params))

        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    
    return decorator



