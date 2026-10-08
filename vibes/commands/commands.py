
from typing import Callable
MISSING = object()

import inspect
from inspect import _empty
from typing import get_args, get_origin, Union
from .params import ALLOWED_CLASSES
from .. import Role

class Command:
    """A VIBES chat command."""
    def __init__(self, **data):
        
        self.name: str = data['name']
        self.callback = data['callback']
        self.role: Role = data['role']
        self.parameters: list[CommandParameter] = data['params']


    async def callback(self, *args):
        raise NotImplementedError("No callback has been implemented for this command")

    def __str__(self):
        return self.name

COMMANDS: list[Command] = []

class CommandParameter:
    def __init__(self, **data):
        self.name: str = data['name']
        self.required: bool = data['required']
        self._type = data['type']



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
    async def ping(ctx):
        await ctx.reply("Pong!")
    ```"""

    def decorator(func: Callable):
        nonlocal name, role
        if name is MISSING:
            name = func.__name__.lower()
        else:
            name = name.lower()


        for command in COMMANDS:
            if command.name == name:
                raise ValueError(f"The command \"{name}\" already exists.")

        params: dict = inspect.signature(func).parameters

        processed_params: list[CommandParameter] = []

        for pname, param in params.items():

            ptype = param.annotation

            origin = get_origin(ptype)
            if origin is Union or origin is __import__("types").UnionType:
                types_list = get_args(ptype)

                ptype = types_list[0] # get the first type

            inner_origin = get_origin(ptype)
            if inner_origin is not None:
                ptype = inner_origin

            if ptype not in ALLOWED_CLASSES:
                raise ValueError(f"Unknown parameter type \"{ptype}\" for \"{pname}\"")
            
            required: bool = param.default is _empty

            processed_params.append(
                CommandParameter(
                    name=pname,
                    type=ptype,
                    required=required
                )
            )


        COMMANDS.append(Command(name=name, callback=func, role=role, params=processed_params))

        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    
    return decorator



