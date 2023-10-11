from utils.models import Game


def get(id: int) -> Game:
    """Get a game by its ID."""
    raise NotImplementedError


def get_all() -> list[Game]:
    """Get all games."""
    raise NotImplementedError
