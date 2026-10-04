import hmac
import os
import secrets
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from flask import current_app, jsonify, redirect, render_template, request, session, url_for

OPEN_ENDPOINTS = {"login", "assets", "health"}
MAX_FAILURES = 5
LOCKOUT_SECONDS = 300
SESSION_DAYS = 7


def _load_secret_key(data_dir):
    configured = os.environ.get("SECRET_KEY")
    if configured:
        return configured
    path = Path(data_dir) / "secret.key"
    if not path.is_file():
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as handle:
                handle.write(secrets.token_hex(32))
        except FileExistsError:
            pass
    for _ in range(20):
        key = path.read_text().strip()
        if key:
            return key
        time.sleep(0.05)
    return secrets.token_hex(32)


def _safe_next(value):
    parsed = urlparse(value or "")
    if parsed.scheme or parsed.netloc or not (value or "").startswith("/") or (value or "").startswith("//"):
        return "/"
    if "\\" in value:
        return "/"
    return value


def configure_auth(app, data_dir):
    password = os.environ.get("ADMIN_PASSWORD", "")
    app.config["ADMIN_PASSWORD"] = password
    if not password:
        return
    app.config.update(
        SECRET_KEY=_load_secret_key(data_dir),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_NAME="edugame_admin",
        PERMANENT_SESSION_LIFETIME=timedelta(days=SESSION_DAYS),
    )
    failures = {}

    def locked(client):
        attempts = [stamp for stamp in failures.get(client, []) if stamp > time.time() - LOCKOUT_SECONDS]
        failures[client] = attempts
        return len(attempts) >= MAX_FAILURES

    @app.before_request
    def require_login():
        if request.endpoint in OPEN_ENDPOINTS or session.get("auth"):
            return None
        if request.path.startswith("/api/"):
            return jsonify(error="Du må logge inn."), 401
        return redirect(url_for("login", next=request.full_path.rstrip("?")))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        target = _safe_next(request.values.get("next"))
        if session.get("auth"):
            return redirect(target)
        error = None
        status = 200
        if request.method == "POST":
            client = request.remote_addr or "unknown"
            if locked(client):
                error = "For mange mislykkede forsøk. Vent noen minutter og prøv igjen."
                status = 429
            elif hmac.compare_digest(
                request.form.get("password", "").encode("utf-8"),
                current_app.config["ADMIN_PASSWORD"].encode("utf-8"),
            ):
                failures.pop(client, None)
                session.clear()
                session["auth"] = True
                session.permanent = True
                return redirect(target)
            else:
                failures.setdefault(client, []).append(time.time())
                error = "Feil passord."
                status = 401
        return render_template("login.html", title="Logg inn", error=error, next=target), status

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))
