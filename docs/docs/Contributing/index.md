# Contribution
Improvements are very welcome, feel free to open a pull request or issue.

Keep in mind this project is aimed towards teachers, so it should be easy to use and understand. Simplicity is more important than performance or fancy features.

## About the modules
The project uses Python, Flask, SQLAlchemy and SQLite, with plain Jinja templates, CSS and JavaScript (no build step). It runs as two separate Flask apps: a read-only public website and an admin interface. The admin interface writes game metadata, file records and site settings to the shared database and stores game files in `games/<Platform>/<game>/`; a password (under Settings or `ADMIN_PASSWORD`) and/or Nginx Proxy Manager is responsible for access control.

| File | Purpose |
| --- | --- |
| `src/app.py` | Both apps, routes, uploads and file storage |
| `src/database.py` | Database models and migrations |
| `src/settings.py` | Site settings (title, logo, front page, menu, pages) |
| `src/auth.py` | Admin login and password changes |
| `src/pages.py` | Default text for the installation guide and terms |
| `src/richtext.py` | HTML sanitizer for teacher notes, the front page text and the pages |
| `src/stores.py` | Store links and Steam/GOG/itch.io/Humble lookups |

The user interface is in Norwegian; the documentation is in English.

See [Setup](Setup-dev.md) to run it locally and the [Roadmap](Roadmap.md) for what is done and what might come next.
