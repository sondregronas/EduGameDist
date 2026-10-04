"""Starter begge appene lokalt med Flask debug (live-reload).

    uv run --directory src python dev.py

Admin kjører på http://localhost:8081 og den offentlige siden på http://localhost:8080.
"""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADMIN_PORT = os.environ.get("ADMIN_PORT", "8081")
PUBLIC_PORT = os.environ.get("PUBLIC_PORT", "8080")


def _wait_for(url, process, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise SystemExit("Admin-appen stoppet under oppstart.")
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except OSError:
            time.sleep(0.3)
    raise SystemExit("Admin-appen startet ikke i tide.")


def _stop(process):
    if os.name == "nt":
        # Flasks reloader starter en barneprosess som må avsluttes sammen med den.
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True)
    else:
        process.terminate()


def main():
    env = {**os.environ, "FLASK_DEBUG": "1", "DATA_DIR": os.environ.get("DATA_DIR", str(HERE / "data"))}
    env.setdefault("PUBLIC_URL", f"http://localhost:{PUBLIC_PORT}/")
    command = [sys.executable, "app.py"]
    # Admin må starte først, siden den oppretter databasen den offentlige siden leser.
    admin = subprocess.Popen([*command, "admin"], cwd=HERE, env={**env, "PORT": ADMIN_PORT})
    processes = [admin]
    try:
        _wait_for(f"http://127.0.0.1:{ADMIN_PORT}/health", admin)
        processes.append(subprocess.Popen([*command, "public"], cwd=HERE, env={**env, "PORT": PUBLIC_PORT}))
        print(f"\nAdmin:   http://localhost:{ADMIN_PORT}\nOffentlig: http://localhost:{PUBLIC_PORT}\nAvslutt med Ctrl+C.\n")
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                _stop(process)
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
