
import inspect
from inspect import Parameter
from typing import get_args, get_origin
from typing import Callable
from .commands import CommandParameter, Command, _UNION_ORIGINS
from .context import _APP_COMMANDS, _EXT_COMMANDS

from .params import _APP_ALLOWED_CLASSES
from ..users import Role, Viewer
from .cooldown import Cooldown

MISSING = object()

TYPES_LABELS = {
    str: 'string',
    int: 'integer',
    float: 'decimal',
    Viewer: 'user'

}


class AppCommand(Command):
    "A VIBES App Command"
    def __init__(self, **data):
        super().__init__(**data)
        self._slug = 'app.' + self.name
        self.description: str = data['description']



    @property
    def _meta(self) -> dict:
        data = {
            'name': self.name,
            'description': self.description,
            'options': []
        }
        descs: dict = getattr(self.callback, '_param_desc', {})
        for param in self.parameters:
            to_add = {
                'name': param.name,
                'description': descs.get(param.name, '...'),
                'type': TYPES_LABELS[param._type],
                'required': param.required

            }
            data['options'].append(to_add)
                


        return data




def describe(**params):
    """## Describe App Command parameters
    ### Example
    ```python
    @commands.app_command()
    @commands.describe(
        name="Your name",
        age="Your age"
    )
    async def introduction(self, ctx, name: str, age: int):
        pass
    ```
    
    """
    def decorator(func: Callable):
        if not params:
            raise ValueError("Empty parameter description")
        if [k for k in params.keys() if not isinstance(k, str)]:
            raise ValueError("Only str() type is accepted when describing command parameters")
        
        func._param_desc = params
        return func

    return decorator

def app_command(name: str = MISSING, description: str = MISSING, *, role: Role = Role.VIEWER, cooldown: Cooldown = None, **kwargs):
    '''Create a new app command.
    - name: The name of the command; if missing, the name of the callback will be used instead
    - role: The minimum required role that can access this command. The available roles:
       - `Role.VIEWER`
       - `Role.MOD`
       - `Role.STREAMER`
    - cooldown: The cooldown rule of the command
    - description: The description of the command; if missing, the description of the callback will be used
    ### Example
    ```python
    @commands.app_command()
    @commands.describe(
        name="Your name!"
    )
    async def hello(ctx, name: str): # "name" is a string parameter typed out by the user
        """Says hello to you!""" # <-- Description visible to the user
        await ctx.reply(f"Hello, {name}! You have {ctx.user.followers} followers!")

    @commands.app_command(role=Role.MOD) # Only moderators & higher can access
    async def ping(ctx): # Must have the first parameter reserved for context
        await ctx.reply("Pong!")
    ```'''

    def decorator(func: Callable):
        nonlocal name, role, description
        if name is MISSING:
            name = func.__name__.lower()
        else:
            name = name.lower()

        qname = func.__qualname__
        if '.' in qname and not kwargs.get('ext'): # If in an unloaded extension
            func._is_app_command = True
            func._command_args = {'name': name, 'role': role, 'cooldown': cooldown, 'description': description} | kwargs
            return func

        description = (description if description is not MISSING else inspect.getdoc(func)) or '...'


        for command in _APP_COMMANDS:
            if command.name == name:
                raise ValueError(f"The app command \"{name}\" already exists.")

        params: dict = inspect.signature(func).parameters

        processed_params: list[CommandParameter] = []

        for i, _p in enumerate(params.items()):
            pname, param = _p 
            if i == 0: # Ignore the ctx param
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

                if ptype not in _APP_ALLOWED_CLASSES:
                    raise ValueError(f"Parameter type \"{ptype}\" for \"{pname}\" can't be proccessed")
            
            required: bool = param.default is Parameter.empty

            processed_params.append(
                CommandParameter(
                    name=pname,
                    type=ptype,
                    required=required,
                    paramclasses=_APP_ALLOWED_CLASSES
                )
            )

        
        obj = AppCommand(name=name, callback=func, required_role=role, 
                        cooldown=cooldown, params=processed_params,
                        description=description)
        _APP_COMMANDS.append(obj)

        # Detect if its in an extension; this way we can remove them if we decide to unload an extension
        if '.' in qname:
            _ext = kwargs['ext']
            if _ext not in _EXT_COMMANDS:
                _EXT_COMMANDS[_ext] = []

            _EXT_COMMANDS[_ext].append(obj)

        return func
    
    return decorator