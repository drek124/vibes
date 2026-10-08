class PremiumSubscription:
    def __init__(self, data: dict):
        self.name: str = data.get('name')
        self.level: int = data.get('level', 0)


async def api_req(coro, *args, allow_errs: list[int] = [], **kwargs):
    """The primary API requests helper B)"""
    while True:
        pass # TODO