# Roadmap
This is a living overview of what has been done and what might come. Suggestions are welcome as an issue or pull request.

## Done
- Python/Flask/SQLAlchemy replaces Node/Pug/NocoDB. The public (read-only) and admin sites run as two separate apps on the same SQLite database.
- A new, modern and mobile-friendly design with built-in icons (no frontend framework or build step).
- Editing directly on the game page, and creating games through a form.
- Several files per platform, uploads without a size limit and a password-protected admin.
- Fetching metadata from Steam (description, cover, developer and website) and automatic search for GOG, itch.io and Humble Bundle links.
- Cover images are stored locally, and older NocoDB data (including covers) is migrated automatically.
- Teacher notes with links and simple HTML.
- Game files are stored under their own names in `games/<Platform>/<game>/`, and older uploads are migrated automatically.
- Site settings in admin: title, logo/favicon, front page text, menu links in any order, the installation guide and terms pages, and the admin password.
- Hiding games from visitors, and filtering by category and platform.

## Possible improvements
- **Users and roles:** several administrators, and possibly access to some games for some users. Admin is currently protected by one shared password and/or the proxy in front of it.
- **Resumable uploads:** large files are sent in one request, so an interrupted upload must start over.
- **More metadata sources:** for example [TheGamesDB](https://thegamesdb.net/) for games that are not on Steam.
- **Better support for large games:** for example checksums and download options per file.
