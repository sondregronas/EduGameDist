<div align="center">

# 🕹️ Game Distribution for Schools 🏫
[![GitHub Pages](https://badgen.net/badge/demo/github%20pages/?icon=chrome)](https://sondregronas.github.io/EduGameDist/)
[![GitHub Pages](https://badgen.net/badge/docs/github%20pages/?icon=chrome)](https://sondregronas.github.io/EduGameDist/docs)
[![Build Status](https://img.shields.io/github/actions/workflow/status/sondregronas/EduGameDist/CI.yml?branch=main)](https://github.com/sondregronas/EduGameDist/)
[![GitHub latest commit](https://img.shields.io/github/last-commit/sondregronas/EduGameDist)](https://github.com/sondregronas/EduGameDist/commit/)

Simple, Docker-based game distribution for schools.
<br>[See the demo.](https://sondregronas.github.io/EduGameDist/)

<img src=".github/media/preview.webp" width="50%">

</div>

> **Disclaimer:** This project is meant for local and internal use. Make sure only people who are entitled to it can reach the website and the files. Check distribution rights and local rules before use.

> **About the use of AI:** Large parts of this project were developed with the help of AI (GitHub Copilot). Review the code yourself before using it in your organization.

The user interface is in Norwegian; the documentation is in English.

## Features

- **Two apps:** a public, read-only website and a separate admin app that share the same database and files.
- **Edit in place:** admin looks like the public site, but with an **Edit** button. Text, categories, links and files are changed where you see them.
- **Several files per platform** (Windows, Mac, Linux, Android), links to files stored elsewhere, and links to browser games. Files are uploaded in one request, stored unchanged under their own name in `games/<Platform>/<game>/`, with no size limit in the app.
- **Hide games** from visitors with the eye icon on the admin dashboard, without deleting them.
- **Light and dark mode** with a switch, following the visitor's system setting until they choose.
- **Shared category list** that games pick from; renaming a category updates every game that has it.
- **Category and platform filters** on the front page. Filtered views can be linked, e.g. `/?category=puzzle`.
- **Import from Steam:** title, description, developer and cover image (downloaded and stored locally). GOG, itch.io and Humble links are looked up automatically.
- **Settings in the browser:** site title, logo/favicon, front page heading and text, menu links (in any order), the installation guide and terms page, and the admin password.
- **Password-protected admin** with a simple login page.
- Existing NocoDB data and older uploads are migrated automatically on startup.

## Installation

Start the services from the folder that contains `docker-compose.yml`:

```bash
ADMIN_PASSWORD=choose-a-password docker compose up -d
```

- The public website is available on port 80.
- Game files are stored in `./games/<Platform>/<game>/` next to `docker-compose.yml`.
- Admin is **not** published on a host port. It is on the Docker network `edugamedist_proxy_access`; connect Nginx Proxy Manager (NPM) to the network and create a proxy host for `admin:8081`.
- Restrict access to both admin and the public site with an NPM Access List or a firewall as needed. Anyone who can reach the public site can download the games.

See the [installation documentation](https://sondregronas.github.io/EduGameDist/docs/Installation/docker/) for proxy, access and upload setup, and [Updating](https://sondregronas.github.io/EduGameDist/docs/Updating/) if you are upgrading an existing installation.

## Local development

With [uv](https://docs.astral.sh/uv/) installed, start both apps with live reload from the project root:

```powershell
uv sync; if ($?) { uv run --directory src python dev.py }
```

That is the PowerShell command. In bash or zsh, use `uv sync && uv run --directory src python dev.py`. Admin runs on <http://localhost:8081> and the public site on <http://localhost:8080>. See the [developer documentation](https://sondregronas.github.io/EduGameDist/docs/Contributing/) for details. Contributions and suggestions are welcome.

## License

The project uses the MIT license. See [LICENSE](LICENSE). The icons come from [Material Design Icons](https://pictogrammers.com/library/mdi/) (Apache-2.0) and [Simple Icons](https://simpleicons.org/) (CC0).
