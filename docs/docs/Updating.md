# Updating
To update your Docker installation, run:
```bash
docker compose pull
docker compose up -d
```

Alternatively you can use something like Watchtower to update your containers automatically. Back up the data volume (`game_db`, plus `game_covers` if you migrated from NocoDB) and the `./games` folder before updating.

## Database changes

The application applies its SQLite schema migrations automatically on startup. Legacy game records, categories, store links, platform downloads and covers are migrated on first startup; the old NocoDB metadata database is no longer used.

## Upgrading to per-game folders and admin settings

This version stores game files as `./games/<Platform>/<game>/<file name>` and moves the site customization into the admin app. Update `docker-compose.yml` along with the image (compare with the [current file](https://github.com/sondregronas/EduGameDist/blob/main/docker-compose.yml)):

1. **Mount `./games` in both services.** The admin service needs write access:

    ```yaml
    admin:
      volumes:
        - ./games:/app/public/games
        - game_db:/app/data
        - game_covers:/app/data/legacy-covers
    frontend:
      volumes:
        - ./games:/app/public/games:ro
        - game_db:/app/data
        - game_covers:/app/data/legacy-covers
    ```

    This replaces the four per-platform mounts (`./games/Windows`, `./games/Mac`, …) on the frontend. The folder layout on the host is the same.

2. **Remove the `./cfg` mounts.** `override.css` and `favicon.ico` are no longer used. Set the title and upload a logo under **Innstillinger** (Settings) instead; see [Personalization](Usage/Personalization.md). The site now uses the system font instead of the Raleway font that `override.css` loaded.

3. **Optional:** add `start_period: 30m` to the admin `healthcheck`, so the frontend waits while existing files are moved (see below).

On the first start with `./games` mounted, the admin app moves existing game files into per-game folders:

- uploads stored under random names in the data volume (`/app/data/uploads`) are moved to `./games/<Platform>/<game>/` under their original names,
- files placed directly in `./games/<Platform>/` by older versions are moved into the folder of the game that uses them (a file used by several games is copied to each).

Moving files from the data volume to `./games` is a copy across filesystems, so the first start can take a while for large libraries. The admin log reports how many files were moved. Files that cannot be found are left as they are and still listed on the game page. Cover images stay in the data volume.

Until `./games` is mounted in the admin container, nothing is moved: new game files keep going to the data volume, and the admin front page shows a warning. This means updating the image before updating `docker-compose.yml` is safe.
