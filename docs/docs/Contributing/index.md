# Contribution
Improvements are very welcome, feel free to open a pull request or issue.

Keep in mind this project is aimed towards teachers, so it should be easy to use and understand. Simplicity is more important than performance or fancy features.

## About the modules
The project uses Python, Flask, SQLAlchemy and SQLite, with plain Jinja templates, CSS and JavaScript (no build step). It runs as two separate Flask apps: a read-only public website and an admin interface. The admin interface writes game metadata and file records to the shared database; a password (`ADMIN_PASSWORD`) and/or Nginx Proxy Manager is responsible for access control.

See [Setup](Setup-dev.md) to run it locally and the [Roadmap](Roadmap.md) for what is done and what might come next.
