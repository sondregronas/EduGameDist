# Installation
The entire project is dockerized, so you can run it using docker-compose. You can also run it without docker, but you will need to install the dependencies manually.

## Docker installation
Make sure you have docker and docker-compose installed.

1. Download the [docker-compose.yml](https://github.com/sondregronas/EduGameDist/blob/main/docker-compose.yml) file from the repository, or see the docker-compose file below.
2. Modify the `docker-compose.yml` file to your liking. (**Note**: Might interfere with updates if you mount more than the `cfg` folders)
3. Run `docker-compose up -d` in the folder where the `docker-compose.yml` file is located.
4. Wait for the containers to start, this may take a while the first time.
5. Visit `<ip-address>:80` in your browser to verify that the frontend is running.

Example `docker-compose.yml`:
```yaml
services:
  frontend:
    image: ghcr.io/sondregronas/edugamedist
    restart: unless-stopped
    ports:
      - 80:80
    volumes:
      # Game installer locations
      - ./games/Windows:/app/public/games/Windows
      - ./games/Mac:/app/public/games/Mac
      - ./games/Linux:/app/public/games/Linux
      - ./games/Android:/app/public/games/Android

      # Configuration files
      - ./cfg:/app/public/cfg
      - ./cfg/views:/app/views/cfg  # (remove trailing /cfg if you want access to all views)
      # - ./cfg/css:/app/public/css

      # Persistent data, leave as is or map to a local folder
      - game_db:/app/db
      - game_covers:/app/public/img
    environment:
      - TITLE=Game Server
  db:
    image: nocodb/nocodb
    restart: unless-stopped
    ports:
      - 8080:8080
    volumes:
      # Persistent data, leave as is or map to a local folder
      - game_db:/usr/app/data/
      - game_covers:/usr/app/data/nc/uploads/noco/Games/Games/Cover
volumes:
  game_db:
  game_covers:
```
