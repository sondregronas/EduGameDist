import hashlib
import hmac
import os
import secrets
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from flask import current_app, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import settings

OPEN_ENDPOINTS = {"login", "assets", "health", "favicon", "site_logo"}
MAX_FAILURES = 5
LOCKOUT_SECONDS = 300
SESSION_DAYS = 7
PASSWORD_SETTING = "admin_password_hash"
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 1000


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


def active_password():
    """The password in use: one saved under Settings wins over ADMIN_PASSWORD. Returns (source, secret)."""
    stored = settings.get(PASSWORD_SETTING)
    if stored:
        return "stored", stored
    configured = current_app.config.get("ADMIN_PASSWORD", "")
    if configured:
        return "env", configured
    return None, ""


def _matches(password, source, secret):
    if source == "stored":
        return check_password_hash(secret, password)
    if source == "env":
        return hmac.compare_digest(password.encode("utf-8"), secret.encode("utf-8"))
    return False


def _fingerprint(source, secret):
    # Stored in the session, so changing the password signs out every other session.
    key = current_app.config["SECRET_KEY"].encode("utf-8")
    return hmac.new(key, f"{source}:{secret}".encode("utf-8"), hashlib.sha256).hexdigest()


def _sign_in():
    source, secret = active_password()
    session.clear()
    if source:
        session["auth"] = _fingerprint(source, secret)
        session.permanent = True


def auth_enabled():
    return active_password()[0] is not None


def logged_in():
    source, secret = active_password()
    return bool(source) and hmac.compare_digest(str(session.get("auth", "")), _fingerprint(source, secret))


def password_status():
    return {"source": active_password()[0], "env_set": bool(current_app.config.get("ADMIN_PASSWORD"))}


def configure_auth(app, data_dir):
    app.config.update(
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", ""),
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

    def verify_current(password):
        """Check the current password for changes made under Settings. Returns an error response or None."""
        source, secret = active_password()
        if not source:
            return None
        client = request.remote_addr or "unknown"
        if locked(client):
            return jsonify(error="For mange mislykkede forsøk. Vent noen minutter og prøv igjen."), 429
        if not _matches(password, source, secret):
            failures.setdefault(client, []).append(time.time())
            return jsonify(error="Nåværende passord er feil."), 403
        failures.pop(client, None)
        return None

    @app.before_request
    def require_login():
        if request.endpoint in OPEN_ENDPOINTS or not auth_enabled() or logged_in():
            return None
        if request.path.startswith("/api/"):
            return jsonify(error="Du må logge inn."), 401
        return redirect(url_for("login", next=request.full_path.rstrip("?")))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        target = _safe_next(request.values.get("next"))
        source, secret = active_password()
        if not source or logged_in():
            return redirect(target)
        error = None
        status = 200
        if request.method == "POST":
            client = request.remote_addr or "unknown"
            if locked(client):
                error = "For mange mislykkede forsøk. Vent noen minutter og prøv igjen."
                status = 429
            elif _matches(request.form.get("password", ""), source, secret):
                failures.pop(client, None)
                _sign_in()
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

    @app.post("/api/settings/password")
    def change_password():
        body = request.get_json(silent=True) or {}
        problem = verify_current(str(body.get("current", "")))
        if problem:
            return problem
        password = str(body.get("password", ""))
        if len(password) < MIN_PASSWORD_LENGTH:
            return jsonify(error=f"Passordet må ha minst {MIN_PASSWORD_LENGTH} tegn."), 400
        if len(password) > MAX_PASSWORD_LENGTH:
            return jsonify(error="Passordet er for langt."), 400
        settings.put({PASSWORD_SETTING: generate_password_hash(password)})
        g.db.commit()
        _sign_in()
        return jsonify(source="stored")

    @app.delete("/api/settings/password")
    def remove_password():
        if active_password()[0] != "stored":
            return jsonify(error="Det finnes ikke noe lagret passord."), 400
        problem = verify_current(str((request.get_json(silent=True) or {}).get("current", "")))
        if problem:
            return problem
        settings.put({PASSWORD_SETTING: None})
        g.db.commit()
        _sign_in()
        return jsonify(source=active_password()[0])
