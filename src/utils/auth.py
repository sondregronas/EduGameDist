"""Decorators for authorization & access control."""

from functools import wraps
from typing import Callable

import flask

from utils.errors import AuthenticationError
from utils.models import User


def requires_access_level(access_level: int) -> Callable:
    """Requires the user to have the specified access level."""

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


def auth_required(func: Callable) -> Callable:
    """Requires the user to be authenticated."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> Callable:
        """The wrapper."""
        user: User = flask.session.get("user")
        if not user:
            raise AuthenticationError("You must be logged in to access this resource.")
        return func(*args, **kwargs)

    return wrapper
