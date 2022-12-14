# EduGameDist (<a href="https://sondregronas.github.io/EduGameDist/">Demo</a>)
[![GitHub Pages](https://badgen.net/badge/demo/github%20pages/?icon=chrome)](https://sondregronas.github.io/EduGameDist/)
[![Build Status](https://img.shields.io/github/workflow/status/sondregronas/EduGameDist/CI)](https://github.com/sondregronas/EduGameDist/)
[![GitHub latest commit](https://img.shields.io/github/last-commit/sondregronas/EduGameDist)](https://github.com/sondregronas/EduGameDist/commit/)

![Frontend](assets/frontend.gif)

Simple game distribution for schools, designed to be easy to use and maintain. Completely dockerized and ready to deploy.

## What is this?
In September of 2022, Spillpedagogene wrote an article ([Skriftlige innspill til Regjeringens Spillstrategi](https://www.spillpedagogene.no/2022/09/01/skriftlige-innspill-til-regjeringens-spillstrategi/)) regarding the logistical struggles of using games in education. Traditionally distribution of games is done by physical medium such as USB drives, or limited to browser based games. This project aims to simplify distribution by providing a way to centralize the game library using a web interface, allowing you to both manage and distribute your own internal game library.

Not every game is eligible for distribution, and you may be required to obtain licenses for some. For information on how to acquire games for distribution, see [this article by spillpedagogbanken (Norwegian)](https://www.spillpedagogbanken.no/?faq=hva-er-steam-epic-itch-io-gog-og-humblebundle).

## Installation
Runs on [Docker](https://www.docker.com/).

Download and read through the [docker-compose.yml](docker-compose.yml) file, modify the environment variables and run `docker-compose up -d` to start the server. Volume mounts are used to persist the database and game files, so you can safely remove the container and recreate it without losing any data. Modify the contents of the `cfg` folder to personalize the frontend, and add games to the `games` folder. You can mostly ignore the `db` folder, as it is used to store the database persistently.

**Please do not expose your instance to the internet, take extra steps to ensure access is limited to your local network.**

> **Note:** Parts of this project is in Norwegian, as it was made for a Norwegian school, you may need to modify all `.pug` files in the `views` folder by uncommenting the volume mount in the `docker-compose.yml` file. This will allow you to edit the files directly on your host machine, and the changes will be reflected in the container.

### Usage
Navigate to the URLs hosted by docker:
- Frontend url: `localhost:80`<br>
- Database url: `localhost:8080`

Login to the database page using the following credentials:
- Default username: `admin@change.me`<br>
- Default password: `changeme`

Be sure to create your own superuser and change the password of the default user.

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
If you own a domain name, you can create an `A-record` pointing to the IP-address of your local server, which will automatically point to port 80. Alternatively, use it in conjunction with [NginxProxyManager](https://nginxproxymanager.com/) to create URLs for both frontend and backend. Be sure to restrict access to the server to only your local network for the frontend, as games WILL be accessible for download from the frontend.

Uploading games remotely can either be done via [network shares (Samba/CIFS)](https://support.microsoft.com/en-us/windows/file-sharing-over-a-network-in-windows-b58704b2-f53a-4b82-7bc1-80f9994725bf#:~:text=To%20share%20a%20file%20or,users%20access%20to%20the%20file.) or by using external drives. For external connections I recommend configuring a protected SFTP server, for example https://hub.docker.com/r/atmoz/sftp.

## Contributing
Refer to [CONTRIBUTING.md](CONTRIBUTING.md) for more information.

## Updates
Currently, there is no simple way of updating your instance in case of database changes, so adding additional features must be done manually. Be sure to create a backup of both `noco.db.defaults` and `gamedb.db` before updating.

I intend to tackle this later, but for now the database columns in `gamedb.db` will not change, so worst case you'll lose out on new features when and if they are added.

## Disclaimer
While this project allows for managing distribution of games or any files over the internet, it's only intended for local and internal use. Take additional precautions to ensure the service is only accessible to those eligible by law in your area. Deploy at your own risk.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
