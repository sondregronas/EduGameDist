# Admin

The admin app is a separate Flask service on port 8081 inside the Docker network `edugamedist_proxy_access`. It does not publish the port on the host, and it can be protected with a password (see [Restricting access](Access.md)). **Nginx Proxy Manager should also decide who gets access.**

Connect the NPM container to the Docker network and create a proxy host for `http://admin:8081`. Choose an NPM Access List with the access rule you want. Do not proxy admin without such a rule, and do not add a public `ports:` mapping.

Open the admin address to add or edit games. Changes become visible on the public site as soon as you save. Files can be uploaded several times per game and platform. See [Docker installation](docker.md) for the settings needed for large uploads.

From the admin front page you can also:

- hide or show a game for visitors with the eye icon on its cover (see [Modifying games](../Usage/Modifying-games.md)),
- open **Innstillinger** (Settings) in the menu to change the title, logo, front page, menu, pages and password (see [Personalization](../Usage/Personalization.md)).
