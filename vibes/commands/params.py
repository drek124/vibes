


async def to_int():
    pass

async def to_float():
    pass

async def to_str():
    pass

ALLOWED_CLASSES = {
    str: to_str,
    int: to_int,
    float: to_float
}