# Restricting access

**Admin can be protected with a password, but should also be restricted by Nginx Proxy Manager (NPM). Do not make the admin service publicly reachable without a password, an NPM Access List or an equivalent rule.**

The admin service is only connected to the Docker network `edugamedist_proxy_access`; Compose publishes no host port for it. Connect the NPM container to the network and send traffic to `admin:8081`.

## Logging in with a password

There are two ways to set the admin password:

1. **Under Innstillinger (Settings) in admin.** The password is stored as a hash in the database and takes precedence over the environment variable. Changing it requires the current password (if one is in use).
2. **With the environment variable `ADMIN_PASSWORD`** for the admin service (in `docker-compose.yml` or an `.env` file next to it):

    ```
    ADMIN_PASSWORD=a-long-and-unique-password
    ```

If a password is saved under Settings, it is used. If it is removed again (**Fjern lagret passord**, Remove saved password), `ADMIN_PASSWORD` applies once more. If neither is set, login is turned off and access is controlled by NPM alone. Saving a password under Settings while login is off turns it on.

With login on, every admin page and API call requires signing in on a login page, and a **Logg ut** (Log out) button appears in the menu. A login lasts 7 days, and after five wrong passwords, logging in is blocked for five minutes. Changing or removing the password signs out everyone else.

Use HTTPS in NPM so the password is not sent unencrypted. Sessions are signed with a key stored in `secret.key` in the data volume; set `SECRET_KEY` if you would rather manage it yourself. Changing the key also signs out everyone.

If you forget a password saved under Settings, remove it from the database to fall back to `ADMIN_PASSWORD`:

```bash
docker compose exec admin python -c "import sqlite3; db = sqlite3.connect('/app/data/gamedb.db'); db.execute(\"DELETE FROM settings WHERE key = 'admin_password_hash'\"); db.commit()"
```

## Public site

Games and files on the public site can be downloaded by anyone who can reach it. Hidden games are not shown and their files cannot be downloaded. Use NPM or a firewall to restrict the frontend if it should only be used on the school network.

## Nginx Proxy Manager

Use [Nginx Proxy Manager](https://nginxproxymanager.com/) for proxy addresses and access rules. Proxy admin to `http://admin:8081` and choose an Access List that fits your organization. Test the rule from a network with and without access.

If you use IP rules, the common private IPv4 ranges are:

```
192.168.0.0/16
172.16.0.0/12
10.0.0.0/8
```

## File access

Games are uploaded through the admin app and stored in `./games/<Platform>/<game>/` on the host. For direct file access (for example backups), use a network share, an external disk or a protected SFTP service. Do not expose the file storage or the admin port directly to the internet.
