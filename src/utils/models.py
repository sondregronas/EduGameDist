"""The data models for the application."""

from dataclasses import dataclass
from pathlib import Path

from enums import Platform, Role


@dataclass
class User:
    """The base user class."""
    name: str
    _access_level: Role
    access_level_override: int = -1

    @property
    def access_level(self) -> int:
        """Returns the user's access level."""
        if self.access_level_override != -1:
            return self.access_level_override
        return self._get_access_level

    @property
    def _get_access_level(self) -> int:
        """Get the user's access level."""
        return self._access_level


@dataclass
class FeideUser(User):
    """The user class for Feide users."""

    @property
    def _get_access_level(self) -> int:
        """Get the user's access level from dataporten groups affiliation."""
        raise NotImplementedError


@dataclass
class GameFile:
    """The base game file class."""
    path: Path | str  # The file's path on disk (must be .zip (which gets packaged by the backend) or URL).
    platform: Platform
    size: int


@dataclass
class GameInfo:
    """The base game info class."""
    title: str
    description: str
    teacher_notes: str
    cover_art: Path

    developer: str
    developer_url: str

    player_count: str  # 1, 1+, 2-4, 2+, etc.
    time_estimate: int  # "15 minutes", "1 hour", etc.
    categories: list[str]  # "Action", "Adventure", "RPG", etc.

    where_to_buy: list[str]  # Links to where the game can be purchased.

    # TODO: Add more fun fields? Such as "is_free", "is_multiplayer", "gallery", "rating", etc.

    @property
    def sort_title(self) -> str:
        """Returns the game's title for sorting."""
        sort_title = self.title.lower()
        if sort_title.startswith("the "):
            sort_title = sort_title[4:]
        return sort_title


@dataclass
class Game:
    """The base game class."""
    id: str  # Slug / unique name
    info: GameInfo
    files: list[GameFile]

    teaching_materials: list[Path]  # relevant PDFs, images, etc.

    visible: bool
    pinned: bool
    public: bool  # Some games can be distributed as "public", such as browser games.

    @property
    def platforms(self) -> list[Platform]:
        """Returns the game's platforms."""
        return [file.platform for file in self.files]
