# Docker installation

EduGameDist consists of two Flask apps that share an SQLite database and file storage:

- **Frontend** shows the games and files. It has no endpoints for changing content.
- **Admin** lets you edit games, upload files and change the site settings. It is not published on a host port; access is controlled by Nginx Proxy Manager (NPM).

## Start

Copy [`docker-compose.yml`](https://github.com/sondregronas/EduGameDist/blob/main/docker-compose.yml) to a folder of its own and start the services:

```bash
docker compose up -d
```

The frontend becomes available on port 80. Docker Compose also creates the network `edugamedist_proxy_access`. Connect the NPM container to it:

```bash
docker network connect edugamedist_proxy_access <NPM container>
```

In NPM, create a Proxy Host with:

- **Forward Hostname / IP:** `admin`
- **Forward Port:** `8081`
- **Scheme:** `http`
- **Access List:** choose a list that only allows approved users or networks

Do not add a `ports:` mapping to the admin service. The Docker network and NPM should be the way into the admin app. Restrict the public frontend with NPM or a firewall as well if the games should not be available to everyone.

For large uploads to work through NPM, add the following to the host's **Advanced** field:

```nginx
client_max_body_size 0;
proxy_request_buffering off;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
```

Files are uploaded in a single streamed request and stored unchanged. `client_max_body_size 0` removes the proxy's size limit, and `proxy_request_buffering off` stops NPM from buffering the whole file on disk first. The app has no upload limit of its own; the real capacity is the free disk space.

## Where data is stored

| Location | Contents |
| --- | --- |
| `./games/<Platform>/<game>/` (bind mount at `/app/public/games`) | Uploaded game files under their original names, e.g. `./games/Windows/oslo-2084/Oslo2084-Setup.zip`. The admin container mounts it read-write, the frontend read-only. |
| `game_db` volume (`/app/data`) | The SQLite database, cover images, the uploaded logo and the session key. |
| `game_covers` volume (`/app/data/legacy-covers`) | Cover images migrated from NocoDB (older installations only). |

The `<game>` folder is the game's address on the site (its slug). When a game is renamed, its folders are renamed with it, and they are removed when the last file is deleted. You can back up or browse `./games` directly, but add and remove files through the admin app so the database stays in sync.

The Docker image only writes game files to `/app/public/games` when it is a mounted volume, so files can never end up inside a container that is replaced on the next update. Without the mount, new game files are kept in the `game_db` volume and admin shows a warning.

## Configuration

| Variable | Service | Purpose |
| --- | --- | --- |
| `ADMIN_PASSWORD` | admin | Password for the admin login. Empty means no login. A password saved under **Innstillinger** (Settings) in admin takes precedence. See [Restricting access](Access.md). |
| `PUBLIC_URL` | admin | Address of the public site, used by the **Åpne nettsiden** (Open website) link in admin. |
| `TITLE` | both | Default site title until one is saved under Settings. |
| `SECRET_KEY` | admin | Optional key for signing login sessions. Generated and stored in `game_db` when not set. |

Everything else (title, logo, front page text, menu, the installation guide and the terms) is changed under **Innstillinger** (Settings) in admin. See [Personalization](../Usage/Personalization.md).

## Existing installations

See [Updating](../Updating.md). The database is migrated automatically on startup, and uploads from older versions are moved into `./games/<Platform>/<game>/`.
