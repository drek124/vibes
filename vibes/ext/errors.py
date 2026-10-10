


class ExtensionNotFound(Exception):
    """The extension could not be imported because it wasn't found."""
    pass
class ExtensionAlreadyLoaded(Exception):
    """The extension is already loaded."""
    pass
class NoEntryPointError(Exception):
    """The extension doesn't have the `setup` function."""
    pass
class ExtensionFailed(Exception):
    """The extension or its `setup` had an execution error."""
    pass




__all__ = [
    "ExtensionNotFound",
    "ExtensionAlreadyLoaded",
    "NoEntryPointError",
    "ExtensionFailed",
]