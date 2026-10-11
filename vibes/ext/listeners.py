from typing import Callable

from .. import events


_LISTENERS: dict[str, dict[str, Callable]] = {}



def _add_event_listener(event:str, handlers: dict, func):
    if event is None:
        event = func.__name__.lower()
    else:
        event = event.lower()

    event = events.ALTERNATIVES.get(event) or event
    if event not in handlers:
        handlers[event] = []

    handlers = handlers[event]
    if func in handlers:
        raise ValueError("Event listener is already listening to this event")
    
    handlers.append(func)

def event_listener(event: str = None):
    """Add an event listener **in an extension**.
    ### Parameters
    - event: The name of the event. If `None`, the name of the callback will be taken instead.
    ### Example
    ```python
    @event_listener()
    async def on_connect():
        print("Logged in successfully!")
    ```"""
    
    def decorator(func: Callable):
        nonlocal event

        qname = func.__qualname__
        if '.' not in qname:
            raise ValueError("This event listener isn't in an extension. Use \"@client.event()\" instead.")

        func._is_event_listener = True
        event = event or func.__name__
        func._event_name = events.ALTERNATIVES.get(event) or event

        return func
    
    
    return decorator