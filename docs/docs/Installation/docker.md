# Installation
The entire project is dockerized, so you can run it using docker-compose. You can also run it without docker, but you will need to install the dependencies manually.

## Docker installation
Make sure you have docker and docker-compose installed.

1. Download the [docker-compose.yml](https://github.com/sondregronas/EduGameDist/blob/main/docker-compose.yml) file from the repository, or see the docker-compose file below.
2. Modify the `docker-compose.yml` file to your liking. See the comments in the file for more information.
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
      - ./games:/app/public/games
      # /app/db is required for persistent storage
      - ./db:/app/db
      - ./db/nc/uploads/noco/Games/Games/Cover:/app/public/img
      # Personalization options
      - ./cfg:/app/public/cfg
      - ./cfg:/app/views/cfg
    environment:
      - TITLE=Game Server
  db:
    image: nocodb/nocodb
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./db:/usr/app/data/
```
