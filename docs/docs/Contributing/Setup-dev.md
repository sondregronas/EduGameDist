# Development setup

Install Python 3.10 or newer and [uv](https://docs.astral.sh/uv/), clone the project and run the command for your shell from the project root:

```powershell
uv sync; if ($?) { uv run --directory src python dev.py }
```

For bash or zsh:

```bash
uv sync && uv run --directory src python dev.py
```

Both commands start the apps with `FLASK_DEBUG=1` (live reload and debugger):

| App | Address |
| --- | --- |
| Admin | <http://localhost:8081> |
| Public site | <http://localhost:8080> |

Stop both with `Ctrl+C`. Python files and templates are reloaded automatically; CSS and JavaScript are read from disk, so reloading the page is enough.

The database, covers and logo are stored in `src/data` (change it with `DATA_DIR`), and uploaded game files in `src/data/games/<Platform>/<game>/` (change it with `GAMES_DIR`). Set `ADMIN_PASSWORD` first if you want to test the login:

```powershell
$env:ADMIN_PASSWORD = "test"; uv sync; if ($?) { uv run --directory src python dev.py }
```

```bash
ADMIN_PASSWORD=test uv sync && ADMIN_PASSWORD=test uv run --directory src python dev.py
```

The ports can be changed with `ADMIN_PORT` and `PUBLIC_PORT`. Run the tests with `uv run --directory src python -m unittest discover -s tests`.

> Debug mode allows running code through the error page and must never be used in production.
