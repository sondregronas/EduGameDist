# EduGameDist (<a href="https://vaagenim.github.io/spill.iktim.no/">Old demo</a>)
[![Build Status](https://img.shields.io/github/workflow/status/sondregronas/EduGameDist/CI)](https://github.com/sondregronas/EduGameDist/)
[![GitHub latest commit](https://img.shields.io/github/last-commit/sondregronas/EduGameDist)](https://github.com/sondregronas/EduGameDist/commit/)

![Frontend](assets/frontend.gif)

A docker based web solution for game distribution in educational environments. Requires control of a local network to function. Please do not expose your instance to the internet, as distributing games without permission is illegal. Ensure only local devices and eligible students have access to the frontend.

> **Note:** Parts of this project is in Norwegian, as it was made for a Norwegian school, you can change this by editing the `.pug` files in the `views` folder by uncommenting the volume mount in the `docker-compose.yml` file.

## What is this?
In September of 2022, Spillpedagogene wrote an article ([Skriftlige innspill til Regjeringens Spillstrategi](https://www.spillpedagogene.no/2022/09/01/skriftlige-innspill-til-regjeringens-spillstrategi/)) regarding the logistical struggles of using games in education. Traditionally distribution of games is done by physical medium such as USB drives, or limited to browser based games. This project aims to simplify distribution by providing a way to centralize the game library using a web interface, allowing you to both manage and distribute your own internal game library.

Not every game is eligible for distribution, and you may be required to obtain licenses for some. For information on how to acquire games for distribution, see [this article by spillpedagogbanken (Norwegian)](https://www.spillpedagogbanken.no/?faq=hva-er-steam-epic-itch-io-gog-og-humblebundle).

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

`games` is where you will put your game installers / binaries in their respective platform folders. It is recommended to store all games in their respective `.zip` archives. Keep note of the filenames, as you will need to point to it in the `New entry` form to add it to your library.

The database comes preconfigured with 3 different views in NocoDB (`localhost:8080`): 
- `Games` (Grid)
- `Friendly` (Gallery view)
- `New entry` (Form)

![Backend](assets/backend.gif)

The `New entry` form can be used to add new games to the database. The `Friendly` view only provides access to the `Cover`, `Time`, `Players`, `Note` and `Categories` fields. I recommend limiting access to the `Friendly` view for your team, and only giving access to `New entry` to administrators.

The `Win_dl`, `Mac_dl` `Android_dl` and `Linux_dl` must point to the filename in their respective `games` subdirectory, OR point to a URL.

> **Note:** The `Note` column allows for unescaped HTML, which allows inputting relevant links or additional files. For example:<br>
> `<a href="games/Windows/MyGame-DLC.zip">DLC</a>` or `<a href="https://<external-site>.pdf">PDF Manual</a>`.
>
> Should you wish to disable this behavior, simply omit the `!` symbol from `p.game-note!=gameData['note']` in [game.pug](https://github.com/sondregronas/EduGameDist/blob/main/src/views/game.pug#L17)

## Recommended setup
If you own a domain name, you can create an `A-record` pointing to the IP-address of your local server, which will automatically point to port 80. Alternatively, use in conjunction with [NginxProxyManager](https://nginxproxymanager.com/) to create URLs for both frontend and backend. Be sure to restrict access to the server to only your local network for the frontend, as games WILL be accessible from the frontend.

Uploading games remotely can either be done via [network shares (Samba/CIFS)](https://support.microsoft.com/en-us/windows/file-sharing-over-a-network-in-windows-b58704b2-f53a-4b82-7bc1-80f9994725bf#:~:text=To%20share%20a%20file%20or,users%20access%20to%20the%20file.) or by using external drives. For external use I recommend configuring a SFTP server, for example using https://hub.docker.com/r/atmoz/sftp.

## Development
Improvements are very welcome, feel free to open a pull request or issue. The CSS and tag structure is a bit of a mess, so feel free to improve it.

Clone the repo and set your working directory to `src`.

Install dependencies using `npm i`.

The dev-mode can be activated by running `npm run dev`, which will automatically refresh the server when changes are made.

## Updates
Currently there is no simple way of updating your instance in case of database changes, so adding additional features must be done manually. Be sure to create a backup of both `noco.db.defaults` and `gamedb.db` before updating.

I intend to tackle this later, but for now the database columns in `gamedb.db` will not change, so worst case you'll lose out on new features when and if they are added.

## Disclaimer
While this project allows for managing distribution of games or any files over the internet, it's only intended for local and internal use. Take additional precautions to ensure the service is only accessible to those eligible by law in your area. It is possible to give access to broader audiences, but in doing so you are operating at your own risk.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
