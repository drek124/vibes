


class Cooldown:

    VIEWER = 1
    USER = 2
    CHAT = 3

    def __init__(self, period: float, max_uses: int = 1, target = VIEWER):
        """## Command Cooldown System
        ### Parameters
        - period: The period in seconds.
        - nax_uses: The amount of times the command can be executed in the `period`
        - target: Who the cooldown applies to. Available values:
          - `Cooldown.VIEWER`: Applies to the user in a specific stream chat only.
          - `Cooldown.USER`: Applies to the user in all streams
          - `Cooldown.CHAT`: Applies to the entirety of a stream chat.
        """

        if max_uses < 1:
            raise ValueError('times value too low')
        
        if period < 1:
            raise ValueError('period value too low')

        if not isinstance(target, int) or target not in (Cooldown.VIEWER, Cooldown.USER, Cooldown.CHAT):
            raise ValueError('Invalid cooldown target')

        self.period: float = period
        self.max_uses: int = max_uses
        self.target = target
