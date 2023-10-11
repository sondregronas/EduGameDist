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


class Role:
    """Roles enum (int)"""
    PUBLIC = 0
    USER = 1
    EDITOR = 2
    ADMIN = 3
    SUPER_ADMIN = 4
