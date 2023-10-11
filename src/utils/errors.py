"""Error handling for the application."""

from functools import wraps
from typing import Callable

import flask


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


def handle_auth_errors(func: Callable) -> Callable:
    """Handles authentication errors."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> Callable:
        """The wrapper."""
        try:
            return func(*args, **kwargs)
        except AuthenticationError as e:
            return flask.abort(401, description=str(e))

    return wrapper
