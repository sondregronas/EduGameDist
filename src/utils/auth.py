"""Decorators for authorization & access control."""

from functools import wraps
from typing import Callable

import flask

from utils.errors import AuthenticationError
from utils.models import User


def auth_required(access_level: int = 0) -> Callable:
    """Requires the user to be authenticated."""

    def decorator(func: Callable) -> Callable:
        """The decorator."""

        @wraps(func)
        def wrapper(*args, **kwargs) -> Callable:
            """The wrapper."""
            user: User = flask.session.get("user")
            if not user:
                raise AuthenticationError("You must be logged in to access this resource.")
            if user.access_level < access_level:
                raise AuthenticationError("You do not have permission to access this resource.")
            return func(*args, **kwargs)

        return wrapper

    return decorator
