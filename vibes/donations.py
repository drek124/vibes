from .users import User

class Donation:
    def __init__(self, data: dict):
        self.streamer: User = data.get('streamer')
        self.user: User = data.get('viewer')
        self.amount: float = data.get('donationAmount')
        self.amount_usd: float = data.get('amountUsd')
        self.currency: str = data.get('currency')
        self.message: str = data.get('dontationMessage')
