"""Settings from the database."""
from backend.db import execute


def set(name: str, value: str) -> None:
    """Set a setting."""
    if get(name):
        execute('UPDATE settings SET value = :value WHERE name = :name', {'name': name, 'value': value})
    else:
        execute('INSERT INTO settings (name, value) VALUES (:name, :value)', {'name': name, 'value': value})


def get(name: str) -> str:
    """Get a setting."""
    try:
        return execute('SELECT value FROM settings WHERE name = :name', {'name': name})[0][0]
    except IndexError:
        return ''
