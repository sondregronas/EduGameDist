# EduGameDist (<a href="https://vaagenim.github.io/spill.iktim.no/">Old demo</a>)
[![Build Status](https://img.shields.io/github/workflow/status/sondregronas/EduGameDist/CI)](https://github.com/sondregronas/EduGameDist/)
[![GitHub latest commit](https://img.shields.io/github/last-commit/sondregronas/EduGameDist)](https://github.com/sondregronas/EduGameDist/commit/)

![Frontend](assets/frontend.gif)

A containerized web based game distribution solution for educational environments. Requires control of a local network to function. Please do not expose your instance to the internet, as it is illegal to distribute games without permission. Ensure only local devices and eligible students have access to the frontend.

> Note: Parts of this project is in Norwegian, as it was made for a Norwegian school, you can change this by editing the `.pug` files in the `views` folder by uncommenting the volume mount in the `docker-compose.yml` file.

## What is this?
Traditionally games have been distributed on physical media. This is a problem, as it requires a lot of physical media, and it is hard to keep track of who has what. This project aims to solve this problem by providing a way to distribute games over a local network.

Not every game is eligible for distribution, and you may be required to obtain licenses for some. For information on how to get access to distribution friendly games, see [this article by spillpedagogbanken (Norwegian)](https://www.spillpedagogbanken.no/?faq=hva-er-steam-epic-itch-io-gog-og-humblebundle).

## Installation
Runs on [Docker](https://www.docker.com/).

Create a `docker-compose.yml`, or download the [docker-compose.yml](docker-compose.yml) file, which includes more options:
```yaml
version: "3.3"
services:
  frontend:
    image: ghcr.io/sondregronas/edugamedist
    restart: unless-stopped
    ports:
      - "80:80"
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

Run using `docker-compose up -d`. A few folders should appear.

Please refer to the docker manual if you wish to customize your ports or volume locations.

## Usage
Navigate to the URLs hosted by docker:
- Frontend url: `localhost:80`<br>
- Database url: `localhost:8080`

You can login to the database page using the following credentials:
- Default username: `admin@change.me`<br>
- Default password: `changeme`

Be sure to create your own superuser and change the password.

The `cfg` folder includes a few files you can modify to personalize your site. 

> **Note that a restart is required for changes to take effect (for `.pug` files only).**

`games` is where you will put your game installers / binaries in their respective platform folders. It is recommended to store all games in their respective `.zip` archives.

The database comes preconfigured with 3 different views in NocoDB (`localhost:8080`): 
- `Games` (Grid)
- `Friendly` (Gallery view)
- `New entry` (Form)

![Backend](assets/backend.gif)

The `New entry` form can be used to add new games to the database. The `Friendly` view allows for changing relevant metadata only.

I recommend only giving access to the `Friendly` view to those who need access, as the hidden values seldom need modification.

The `Note` column allows for unescaped HTML, which allows inputting relevant links or additional files. For example:<br>
`<a href="games/Windows/MyGame-DLC.zip">DLC</a>` or `<a href="https://<external-site>.pdf">PDF Manual</a>`.

## Recommended setup
If you own a domain name, you can create an `A-record` pointing to the IP-adress of your local server, which will automatically point to port 80. Alternatively, use in conjunction with [NginxProxyManager](https://nginxproxymanager.com/) to create URLs for both frontend and backend. Be sure to restrict access to the server to only your local network for the frontend, as games WILL be accessible from the frontend.

Uploading games remotely can either be done via [network shares (Samba/CIFS)](https://support.microsoft.com/en-us/windows/file-sharing-over-a-network-in-windows-b58704b2-f53a-4b82-7bc1-80f9994725bf#:~:text=To%20share%20a%20file%20or,users%20access%20to%20the%20file.) or by using external drives. For external use I recommend configuring a SFTP server, for example using https://hub.docker.com/r/atmoz/sftp.

## Development
Improvements are very welcome, feel free to open a pull request or issue. The CSS and tag structure is a bit of a mess, so feel free to improve it.

Clone the repo and set your working directory to `src`.

Install dependencies using `npm i`.

The dev-mode can be activated by running `npm run dev`, which will automatically refresh the server when changes are made.

## Updates
Currently there is no simple way of updating your instance in case of database changes, so adding additional features must be done manually. Be sure to create a backup of both `noco.db.defaults` and `gamedb.db` before updating.

I intend to tackle this later, but for now the database columns in `gamedb.db` will not change, so worst case you'll lose out on new features when and if they are added.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
