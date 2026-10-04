# Contribution
Improvements are very welcome, feel free to open a pull request or issue. The frontend in general is a bit of a mess, so feel free to improve it. Design is not my strong suit.

Keep in mind this project is aimed towards teachers, so it should be easy to use and understand. Performance or fancy features are not a priority, simplicity is.

## About the modules
The project uses Python, Flask, SQLAlchemy, and SQLite. It runs as two separate Flask apps: a read-only public website and an admin interface. The admin interface writes game metadata and file records to the shared database; Nginx Proxy Manager is responsible for access control.