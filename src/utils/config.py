"""Global configuration variables, set by either .env or using defaults."""
import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_NAME = os.getenv('DATABASE_NAME', 'db.sqlite3')
MOCK_DATA = os.getenv('MOCK_DATA', 'true').lower() in ['true', '1', 'y', 'yes']

if MOCK_DATA:
    DATABASE_NAME = 'mock.sqlite3'
