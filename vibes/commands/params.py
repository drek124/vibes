


def _vanilla(datatype): # Default handler; unnecessary to make a callback for default classes such as float & int
    async def c(text: str):
        return datatype(text)
    return c
    

_ALLOWED_CLASSES = {
    str: _vanilla(str),
    int: _vanilla(int),
    float: _vanilla(float)
}