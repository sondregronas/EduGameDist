# EduGameDist (<a href="https://vaagenim.github.io/spill.iktim.no/">Old demo</a>)
[![Build Status](https://img.shields.io/github/workflow/status/sondregronas/EduGameDist/CI)](https://github.com/sondregronas/EduGameDist/)
[![GitHub latest commit](https://img.shields.io/github/last-commit/sondregronas/EduGameDist)](https://github.com/sondregronas/EduGameDist/commit/)

A containerized web based game distribution solution for educational settings. Requires access to the schools local network in order to work. You should never expose this to the internet, as it is illegal to distribute games without permission. Ensure only local devices and students have access to the server.

Note: Parts of this project is in Norwegian, as it was made for a Norwegian school, you can change this by editing the `.pug` files in the `views` folder by uncommenting the volume mount in the `docker-compose.yml` file.

## What is this?
Traditionally games have been distributed on physical media. This is a problem for schools, as they have to buy a lot of physical media, and it is hard to keep track of who has what. This project aims to solve this problem by providing a way to distribute games over a local network.

For information on how to get access to distribution friendly games, see [this article by spillpedagogene (Norwegian)](https://www.spillpedagogbanken.no/?faq=hva-er-steam-epic-itch-io-gog-og-humblebundle).

## Setup
Runs on [Docker](https://www.docker.com/).

Create a `docker-compose.yml`, or download the [docker-compose.yml](docker-compose.yml) file:
```yaml
version: "3.3"
services:
  frontend:
    image: ghcr.io/sondregronas/edugamedist
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      # Note, you can also bind any folder to a network share or different directories
      - ./games:/app/public/games
      - ./cfg:/app/public/cfg
      - ./db:/app/db
      - ./db/nc/uploads/noco/Games/Games/Cover:/app/public/img

      # Choose between only a few select view-files, or the entire view folder.
      - ./cfg:/app/views/cfg
      # - ./cfg/views:/app/views

      # Uncomment for full CSS access
      # - ./cfg/css:/app/public/css

      # Uncomment for full access (not recommended)
      # - ./app:/app
  db:
    image: nocodb/nocodb
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./db:/usr/app/data/
```

Run using `docker-compose up -d`. A few folders should appear.

## Usage
Navigate to the URLs hosted by docker:
- Frontend url: `localhost`<br>
- Database url: `localhost:8080`

You can login to the database page using the following credentials:
- Default username: `admin@change.me`<br>
- Default password: `changeme`

Be sure to create your own superuser and change the password.

The `cfg` folder includes a few files you can modify to personalize your site. 

`games` is where you will put your game installers / binaries in their respective platform folders. It is recommended to store all games in their respective `.zip` archives.

> **Note that a restart is required for changes to take effect (for `.pug` files only).**

The database comes preconfigured with 3 different views in NocoDB (`localhost:8080`): 
- `Games` (Grid)
- `Friendly` (Gallery view)
- `New entry` (Form)

![img](assets/form.png)

The `New entry` form can be used to add new games to the database. The `Friendly` view allows for changing relevant metadata only.

I recommend only giving access to the `Friendly` view to those who need access, as the hidden values seldom need modification.

## Recommended setup
Use in conjunction with [NginxProxyManager](https://nginxproxymanager.com/) to get a nice URL for both the frontend and database. Be sure to restrict access to the server to only your local network for the frontend, as games will be accessible from the frontend.

## Development
Clone the repo and set your working directory to `src`.<br>
Install dependencies using `npm i`.<br>
The dev-mode can be activated by running `npm run dev`, which will automatically refresh the server when changes are made.<br>

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
