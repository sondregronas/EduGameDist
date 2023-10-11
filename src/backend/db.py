"""Database connection and queries."""
import os
import sqlite3

import utils.config as config


class connect:
    """Database connection with cursor"""

    def __init__(self, commit_on_close: bool = True) -> None:
        """Initialize the connection and cursor."""
        self.conn = sqlite3.connect(config.DATABASE_NAME)
        self.cursor = self.conn.cursor()
        self.commit_on_close = commit_on_close

    def __enter__(self) -> tuple[sqlite3.Connection, sqlite3.Cursor]:
        """Return a tuple of the connection and cursor."""
        return self.conn, self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Commit and close the connection."""
        if self.commit_on_close:
            self.conn.commit()
        self.conn.close()


def execute(query: str, data: dict = {}) -> list[tuple]:
    """Execute a query and return the results."""
    with connect() as (conn, cursor):
        cursor.execute(query, data)
        return cursor.fetchall()


def execute_script(sql_file: str) -> None:
    """Execute the SQL query from the sql directory."""
    with open(sql_file) as f:
        [execute(query.strip()) for query in f.read().split(';')]


def add_mock_data():
    """Add mock data to the database."""
    execute_script('sql/mock_data.sql')


def init_db():
    """Initialize the database."""
    if config.MOCK_DATA and os.path.exists(config.DATABASE_NAME):
        os.remove(config.DATABASE_NAME)
    if not os.path.exists(config.DATABASE_NAME):
        execute_script('sql/create_tables.sql')
        execute_script('sql/first_run.sql')
    if config.MOCK_DATA:
        add_mock_data()


if __name__ == '__main__':
    init_db()  # Test only
