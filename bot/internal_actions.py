"""Plain decorators for panel-only actions that are not Discord commands."""


def internalAction(*args, **kwargs):
    """Preserve a readable action marker without registering an app command."""

    def decorator(callback):
        return callback

    return decorator


class InternalActionGroup:
    """Provide group-like decoration while keeping callbacks ordinary methods."""

    command = staticmethod(internalAction)
