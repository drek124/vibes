
from ..users import Viewer

def _vanilla(datatype): # Default handler; unnecessary to make a callback for default classes such as float & int
    async def c(text: str, client):
        return datatype(text)
    return c
    

_ALLOWED_CLASSES = {
    str: _vanilla(str),
    int: _vanilla(int),
    float: _vanilla(float)
}

async def get_viewer(data: dict, client):
    return Viewer(data, client)


_APP_ALLOWED_CLASSES = {
    Viewer: get_viewer
} | _ALLOWED_CLASSES