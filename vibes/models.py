class PremiumSubscription:
    def __init__(self, data: dict):
        self.name: str = data.get('name')
        self.level: int = data.get('level', 0)