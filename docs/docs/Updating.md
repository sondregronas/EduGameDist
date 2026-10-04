# Updating
To update your docker instance, you can use the following commands:
```bash
docker-compose pull
docker-compose up -d
```

Alternatively you can use something like Watchtower to automatically update your containers.

## Database changes

The application applies its SQLite schema migrations automatically on startup. Back up both Docker volumes (`game_db` and `game_covers`) before updating. Legacy game records, categories, store links and platform downloads are migrated on first startup; the old NocoDB metadata database is no longer used.