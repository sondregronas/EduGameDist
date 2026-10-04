# Utviklingsmiljø

Installer Python 3.10 eller nyere og [uv](https://docs.astral.sh/uv/), klon prosjektet og kjør kommandoen som passer skallet ditt fra prosjektroten:

```powershell
uv sync; if ($?) { uv run --directory src python dev.py }
```

For bash eller zsh:

```bash
uv sync && uv run --directory src python dev.py
```

Begge kommandoene starter appene med `FLASK_DEBUG=1` (live-reload og debugger):

| App | Adresse |
| --- | --- |
| Admin | <http://localhost:8081> |
| Offentlig side | <http://localhost:8080> |

Avslutt begge med `Ctrl+C`. Python-filer og maler lastes inn på nytt automatisk; CSS og JavaScript leses fra disk, så det holder å laste siden på nytt.

Databasen og opplastede filer ligger i `src/data` (kan endres med `DATA_DIR`). Sett `ADMIN_PASSWORD` først hvis du vil teste innloggingen:

```powershell
$env:ADMIN_PASSWORD = "test"; uv sync; if ($?) { uv run --directory src python dev.py }
```

```bash
ADMIN_PASSWORD=test uv sync && ADMIN_PASSWORD=test uv run --directory src python dev.py
```

Porter kan endres med `ADMIN_PORT` og `PUBLIC_PORT`. Kjør testene med `uv run --directory src python -m unittest discover -s tests`.

> Debug-modus tillater kjøring av kode gjennom feilsiden og skal aldri brukes ved utrulling.
