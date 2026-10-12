
class NotFound(Exception):
    """Raised when the API returns a 404 Not Found response."""
    pass


class Forbidden(Exception):
    """Raised when the API returns a 403 Forbidden response."""
    pass


__all__ = [
    "NotFound",
    "Forbidden",
]