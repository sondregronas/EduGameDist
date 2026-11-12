# Restricting access

**Admin can be protected with a password and/or GitHub login, but should also be restricted by Nginx Proxy Manager (NPM). Do not make the admin service publicly reachable without a login, an NPM Access List or an equivalent rule.**

The admin service is only connected to the Docker network `edugamedist_proxy_access`; Compose publishes no host port for it. Connect the NPM container to the network and send traffic to `admin:8081`.

## Logging in with a password

There are two ways to set the admin password:

1. **Under Innstillinger (Settings) in admin.** The password is stored as a hash in the database and takes precedence over the environment variable. Changing it requires the current password (if one is in use).
2. **With the environment variable `ADMIN_PASSWORD`** for the admin service (in `docker-compose.yml` or an `.env` file next to it):

    ```
    ADMIN_PASSWORD=a-long-and-unique-password
    ```

If a password is saved under Settings, it is used. If it is removed again (**Fjern lagret passord**, Remove saved password), `ADMIN_PASSWORD` applies once more. If neither is set and [GitHub login](#logging-in-with-github) is not set up, login is turned off and access is controlled by NPM alone. Saving a password under Settings while login is off turns it on.

With login on, every admin page and API call requires signing in on a login page, and a **Logg ut** (Log out) button appears in the menu. A login lasts 7 days, and after five wrong passwords, logging in is blocked for five minutes. Changing or removing the password signs out everyone else who signed in with it (GitHub users stay signed in).

## Logging in with GitHub

Chosen GitHub users can sign in to admin with their GitHub account, in addition to (or instead of) the password. Everything is set up under **Innstillinger → GitHub-innlogging** (Settings → GitHub login); no environment variables or restarts are needed.

1. Create an OAuth App on GitHub: [github.com/settings/applications/new](https://github.com/settings/applications/new), or **Settings → Developer settings → OAuth Apps** in an organization. The settings page shows the **Homepage URL** and **Authorization callback URL** to use, with copy buttons. The callback URL is the admin address followed by `/login/github/callback`, e.g. `https://admin.example.com/login/github/callback`.
2. Paste the **Client ID** and a newly generated **Client secret** into the settings page and press **Lagre GitHub-appen** (Save the GitHub app). The secret is only visible while you paste it: after saving it is never sent back to the browser, only its last four characters are shown (`••••abcd`). Use **Bytt** (Replace) to save a new one.
3. Under **Brukere med tilgang** (Users with access), add GitHub users by name, `@name` or a link to their profile. Each name is looked up on GitHub and stored with the account's numeric id, so the user can still sign in after renaming their account, and a new account that takes an old name does not get in.

GitHub login turns on once the app is saved and at least one user has access. The login page then shows **Logg inn med GitHub** (Log in with GitHub), next to the password field if a password is also in use. If no password is set, GitHub is the only way in. The app only asks GitHub for the user's public profile, and the GitHub token is not stored.

Changes to the GitHub app and the user list are confirmed with the admin password. A user who is signed in with GitHub and has access can make them without the password. Removing a user signs them out straight away; removing the app signs out every GitHub user.

The admin service fetches the login from `github.com` and `api.github.com`, so it needs outgoing HTTPS access to them.

### Resetting the admin password as a GitHub user

A user signed in with GitHub can replace the admin password without knowing it: enter the new password twice under **Passord for admin**, type `SETADMIN` in the confirmation field and save. **Fjern lagret passord** works the same way. Everyone who signed in with the old password is signed out.

Use HTTPS in NPM so the password is not sent unencrypted. Sessions are signed with a key stored in `secret.key` in the data volume; set `SECRET_KEY` if you would rather manage it yourself. Changing the key also signs out everyone.

If you forget a password saved under Settings, set `FORCE_ENV_PASSWORD=true` (see [below](#environment-variables-that-override-settings)) and log in with `ADMIN_PASSWORD`. To remove the saved password for good, delete it from the database:

```bash
docker compose exec admin python -c "import sqlite3; db = sqlite3.connect('/app/data/gamedb.db'); db.execute(\"DELETE FROM settings WHERE key = 'admin_password_hash'\"); db.commit()"
```

### Turning password login off

When GitHub login works, you can allow GitHub users only: untick **Tillat innlogging med passord** (Allow password login) under **Passord for admin**. The login page then only offers GitHub, and everyone signed in with the password is signed out. To make sure GitHub login actually works, the switch can only be turned off by someone who is signed in with GitHub.

The password is kept, and comes back on by itself if GitHub login stops being set up (the GitHub app is removed, or the last user loses access), so nobody is locked out. A GitHub user can tick the switch again at any time.

### Environment variables that override Settings

Set these for the admin service in `docker-compose.yml` (or an `.env` file) and restart it, for example to get back in:

| Variable | Effect |
| --- | --- |
| `FORCE_PASSWORD_LOGIN=true` | Logging in with the password is always allowed, even if it is turned off under Settings. The switch is locked on. |
| `FORCE_ENV_PASSWORD=true` | Only `ADMIN_PASSWORD` is used. A password saved under Settings is ignored (but kept), and the password cannot be changed or removed there. |

Both default to `false`. `FORCE_ENV_PASSWORD` with an empty `ADMIN_PASSWORD` means there is no password at all.

If GitHub login is the only login and the GitHub app stops working (for example after the secret was revoked), set `ADMIN_PASSWORD` (and `FORCE_PASSWORD_LOGIN=true` if password login was turned off) for the admin service and restart it to get back in with the password.

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
