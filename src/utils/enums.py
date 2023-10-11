"""Enums for the project."""

from enum import Enum, auto


class Platform(Enum):
    """Platform enum."""
    WINDOWS = auto()
    LINUX = auto()
    MACOS = auto()
    ANDROID = auto()
    IOS = auto()
    WEB = auto()
    UNKNOWN = auto()
