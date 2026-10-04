"""Start both apps locally with Flask debug (live reload).

    uv run --directory src python dev.py

Admin runs on http://localhost:8081 and the public site on http://localhost:8080.
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
            raise SystemExit("The admin app stopped during startup.")
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except OSError:
            time.sleep(0.3)
    raise SystemExit("The admin app did not start in time.")


def _stop(process):
    if os.name == "nt":
        # Flask's reloader starts a child process that must be stopped along with it.
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True)
    else:
        process.terminate()


def main():
    data_dir = os.environ.get("DATA_DIR", str(HERE / "data"))
    env = {
        **os.environ,
        "FLASK_DEBUG": "1",
        "DATA_DIR": data_dir,
        # Uploaded game files stay out of the source tree during development.
        "GAMES_DIR": os.environ.get("GAMES_DIR", str(Path(data_dir) / "games")),
    }
    env.setdefault("PUBLIC_URL", f"http://localhost:{PUBLIC_PORT}/")
    command = [sys.executable, "app.py"]
    # Admin must start first, since it creates the database the public site reads.
    admin = subprocess.Popen([*command, "admin"], cwd=HERE, env={**env, "PORT": ADMIN_PORT})
    processes = [admin]
    try:
        _wait_for(f"http://127.0.0.1:{ADMIN_PORT}/health", admin)
        processes.append(subprocess.Popen([*command, "public"], cwd=HERE, env={**env, "PORT": PUBLIC_PORT}))
        print(f"\nAdmin:  http://localhost:{ADMIN_PORT}\nPublic: http://localhost:{PUBLIC_PORT}\nStop with Ctrl+C.\n")
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
