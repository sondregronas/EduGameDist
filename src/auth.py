"""Signing in to admin: with the admin password, with GitHub (for the users allowed under Settings), or both.

Login is required as soon as one of them is set up. Changing who can sign in needs the admin password,
unless the change is made by a GitHub user who is allowed to sign in.

Two environment variables override Settings, e.g. to get back in:
- FORCE_PASSWORD_LOGIN: logging in with the password is always allowed.
- FORCE_ENV_PASSWORD: only ADMIN_PASSWORD is used; a password saved under Settings is ignored and the
  password cannot be changed there.
"""
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

import github
import settings

OPEN_ENDPOINTS = {"login", "github_login", "github_callback", "assets", "health", "favicon", "site_logo"}
MAX_FAILURES = 5
LOCKOUT_SECONDS = 300
SESSION_DAYS = 7
PASSWORD_SETTING = "admin_password_hash"
# "off" turns password login off, which is only possible (and only lasts) while GitHub login works.
PASSWORD_LOGIN_SETTING = "password_login"
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 1000
# A signed-in GitHub user can replace the admin password without knowing it by typing this word.
RESET_WORD = "SETADMIN"
LOCKED = "For mange mislykkede forsøk. Vent noen minutter og prøv igjen."


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


def _flag(name):
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def active_password():
    """The password in use: one saved under Settings wins over ADMIN_PASSWORD, unless FORCE_ENV_PASSWORD
    is set. Returns (source, secret)."""
    stored = None if current_app.config.get("FORCE_ENV_PASSWORD") else settings.get(PASSWORD_SETTING)
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
    # Stored in the session, so changing the password signs out every other password session.
    key = current_app.config["SECRET_KEY"].encode("utf-8")
    return hmac.new(key, f"{source}:{secret}".encode("utf-8"), hashlib.sha256).hexdigest()


def _sign_in():
    """Start a password session, or end the session if there is no longer a password."""
    source, secret = active_password()
    session.clear()
    if source:
        session["auth"] = _fingerprint(source, secret)
        session.permanent = True


def auth_enabled():
    return active_password()[0] is not None or github.active()


def password_login_allowed():
    """Whether the password can be used to log in. It can be turned off under Settings, but is always on
    with FORCE_PASSWORD_LOGIN, and comes back on by itself when GitHub login is not set up, so nobody
    is locked out."""
    if active_password()[0] is None:
        return False
    if current_app.config.get("FORCE_PASSWORD_LOGIN"):
        return True
    return settings.get(PASSWORD_LOGIN_SETTING) != "off" or not github.active()


def _password_session():
    source, secret = active_password()
    return (
        password_login_allowed()
        and hmac.compare_digest(str(session.get("auth", "")), _fingerprint(source, secret))
    )


def github_user():
    """The allowed GitHub user this session is signed in as, or None. Removing the user ends the session."""
    signed_in = session.get("github")
    if not isinstance(signed_in, dict) or not github.configured():
        return None
    return github.find_user(signed_in.get("id"))


def logged_in():
    return _password_session() or github_user() is not None


def password_status():
    user = github_user()
    return {
        "source": active_password()[0],
        "env_set": bool(current_app.config.get("ADMIN_PASSWORD")),
        "github_session": user is not None,
        "github_active": github.active(),
        "reset_word": RESET_WORD,
        "login_allowed": password_login_allowed(),
        "login_setting": settings.get(PASSWORD_LOGIN_SETTING) != "off",
        "force_login": bool(current_app.config.get("FORCE_PASSWORD_LOGIN")),
        "force_env": bool(current_app.config.get("FORCE_ENV_PASSWORD")),
        "stored_ignored": bool(current_app.config.get("FORCE_ENV_PASSWORD") and settings.get(PASSWORD_SETTING)),
    }


def github_status():
    """What the settings page shows about GitHub sign-in. Never includes the client secret."""
    user = github_user()
    return {
        "client_id": github.client_id(),
        "secret_hint": github.secret_hint(),
        "configured": github.configured(),
        "active": github.active(),
        "users": github.users(),
        "signed_in_as": user["id"] if user else None,
        "needs_password": user is None and active_password()[0] is not None,
        "login_required": auth_enabled(),
        "callback_path": github.CALLBACK_PATH,
    }


def _failures():
    return current_app.extensions.setdefault("login_failures", {})


def _client():
    return request.remote_addr or "unknown"


def _locked():
    failures = _failures()
    attempts = [stamp for stamp in failures.get(_client(), []) if stamp > time.time() - LOCKOUT_SECONDS]
    failures[_client()] = attempts
    return len(attempts) >= MAX_FAILURES


def _failed():
    _failures().setdefault(_client(), []).append(time.time())


def verify_current(password):
    """Check the current password for changes made under Settings. Returns an error response or None."""
    source, secret = active_password()
    if not source:
        return None
    if _locked():
        return jsonify(error=LOCKED), 429
    if not _matches(password, source, secret):
        _failed()
        return jsonify(error="Nåværende admin-passord er feil."), 403
    _failures().pop(_client(), None)
    return None


def _authorize_access_change(body):
    """Who may sign in is changed with the admin password, or by an allowed GitHub user."""
    if github_user():
        return None
    return verify_current(str(body.get("current", "")))


def _authorize_password_change(body):
    """The password is changed with the current one. A signed-in GitHub user types RESET_WORD instead."""
    if github_user() and active_password()[0]:
        if str(body.get("confirm", "")).strip() != RESET_WORD:
            return jsonify(error=f"Skriv {RESET_WORD} for å bekrefte at du vil bytte admin-passordet."), 403
        return None
    return verify_current(str(body.get("current", "")))


def _after_password_change():
    # Every other password session is signed out. GitHub sessions do not depend on the password.
    if not github_user():
        _sign_in()


def _added_by():
    user = github_user()
    return f"@{user['login']}" if user else "admin-passordet" if _password_session() else ""


def configure_auth(app, data_dir):
    app.config.update(
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", ""),
        SECRET_KEY=_load_secret_key(data_dir),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_NAME="edugame_admin",
        PERMANENT_SESSION_LIFETIME=timedelta(days=SESSION_DAYS),
        FORCE_PASSWORD_LOGIN=_flag("FORCE_PASSWORD_LOGIN"),
        FORCE_ENV_PASSWORD=_flag("FORCE_ENV_PASSWORD"),
    )

    @app.context_processor
    def signed_in_user():
        return {"github_user": github_user()}

    @app.before_request
    def require_login():
        if request.endpoint in OPEN_ENDPOINTS or not auth_enabled() or logged_in():
            return None
        if request.path.startswith("/api/"):
            return jsonify(error="Du må logge inn."), 401
        return redirect(url_for("login", next=request.full_path.rstrip("?")))

    def login_page(target, error=None, status=200):
        return render_template(
            "login.html",
            title="Logg inn",
            error=error,
            next=target,
            password_login=password_login_allowed(),
            github_login=github.active(),
        ), status

    @app.route("/login", methods=["GET", "POST"])
    def login():
        target = _safe_next(request.values.get("next"))
        if not auth_enabled() or logged_in():
            return redirect(target)
        if request.method == "GET":
            return login_page(target)
        source, secret = active_password()
        if not password_login_allowed():
            return login_page(target, "Innlogging med passord er slått av. Logg inn med GitHub.", 400)
        if _locked():
            return login_page(target, LOCKED, 429)
        if not _matches(request.form.get("password", ""), source, secret):
            _failed()
            return login_page(target, "Feil passord.", 401)
        _failures().pop(_client(), None)
        _sign_in()
        return redirect(target)

    @app.get("/login/github")
    def github_login():
        target = _safe_next(request.args.get("next"))
        if not auth_enabled() or logged_in():
            return redirect(target)
        if not github.active():
            return login_page(target, "Innlogging med GitHub er ikke satt opp.", 400)
        state = secrets.token_urlsafe(32)
        session["github_oauth"] = {"state": state, "next": target}
        return redirect(github.authorize_url(state))

    @app.get(github.CALLBACK_PATH)
    def github_callback():
        pending = session.pop("github_oauth", None)
        pending = pending if isinstance(pending, dict) else {}
        target = _safe_next(pending.get("next"))
        state = request.args.get("state", "")
        if not state or not hmac.compare_digest(str(pending.get("state", "")), state):
            return login_page(target, "Innloggingen med GitHub er utløpt eller ble startet et annet sted. Prøv igjen.", 400)
        if request.args.get("error"):
            return login_page(target, "Innloggingen med GitHub ble avbrutt.", 400)
        code = request.args.get("code", "")
        if not github.active() or not code or len(code) > 500:
            return login_page(target, "Innlogging med GitHub er ikke satt opp.", 400)
        try:
            account = github.sign_in(code)
        except github.GitHubError as error:
            current_app.logger.warning("GitHub sign-in failed: %s", error)
            return login_page(target, str(error), 502)
        if not github.find_user(account["id"]):
            return login_page(target, f"GitHub-brukeren @{account['login']} har ikke tilgang til admin. Be en administrator legge deg til under Innstillinger.", 403)
        github.refresh_login(account)
        g.db.commit()
        session.clear()
        session["github"] = {"id": account["id"], "login": account["login"]}
        session.permanent = True
        return redirect(target)

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    def env_password_only():
        if current_app.config["FORCE_ENV_PASSWORD"]:
            return jsonify(error="Passordet styres av ADMIN_PASSWORD, fordi FORCE_ENV_PASSWORD er slått på."), 400
        return None

    @app.post("/api/settings/password")
    def change_password():
        body = request.get_json(silent=True) or {}
        problem = env_password_only() or _authorize_password_change(body)
        if problem:
            return problem
        password = str(body.get("password", ""))
        if len(password) < MIN_PASSWORD_LENGTH:
            return jsonify(error=f"Passordet må ha minst {MIN_PASSWORD_LENGTH} tegn."), 400
        if len(password) > MAX_PASSWORD_LENGTH:
            return jsonify(error="Passordet er for langt."), 400
        settings.put({PASSWORD_SETTING: generate_password_hash(password)})
        g.db.commit()
        _after_password_change()
        return jsonify(source="stored")

    @app.delete("/api/settings/password")
    def remove_password():
        problem = env_password_only()
        if problem:
            return problem
        if active_password()[0] != "stored":
            return jsonify(error="Det finnes ikke noe lagret passord."), 400
        problem = _authorize_password_change(request.get_json(silent=True) or {})
        if problem:
            return problem
        settings.put({PASSWORD_SETTING: None})
        g.db.commit()
        _after_password_change()
        return jsonify(source=active_password()[0], login_required=auth_enabled())

    @app.put("/api/settings/password-login")
    def set_password_login():
        body = request.get_json(silent=True) or {}
        enabled = body.get("enabled")
        if not isinstance(enabled, bool):
            return jsonify(error="Velg av eller på."), 400
        if current_app.config["FORCE_PASSWORD_LOGIN"]:
            return jsonify(error="Innlogging med passord er alltid på, fordi FORCE_PASSWORD_LOGIN er satt."), 400
        # Only someone who has just logged in with GitHub can turn the password off, so it is known to work.
        if not enabled and not github_user():
            return jsonify(error="Logg inn med GitHub før du slår av innlogging med passord, så du vet at GitHub-innloggingen virker."), 403
        problem = _authorize_access_change(body)
        if problem:
            return problem
        settings.put({PASSWORD_LOGIN_SETTING: None if enabled else "off"})
        g.db.commit()
        return jsonify(password_status())

    @app.put("/api/settings/github")
    def save_github():
        body = request.get_json(silent=True) or {}
        problem = _authorize_access_change(body)
        if problem:
            return problem
        try:
            values = github.validated_credentials(body)
        except ValueError as error:
            return jsonify(error=str(error)), 400
        settings.put(values)
        g.db.commit()
        return jsonify(github_status())

    @app.delete("/api/settings/github")
    def remove_github():
        problem = _authorize_access_change(request.get_json(silent=True) or {})
        if problem:
            return problem
        # The list of users is kept, so GitHub sign-in works again when a new OAuth app is saved.
        settings.put({github.CLIENT_ID: None, github.CLIENT_SECRET: None})
        g.db.commit()
        return jsonify(github_status())

    @app.post("/api/settings/github/users")
    def add_github_user():
        body = request.get_json(silent=True) or {}
        problem = _authorize_access_change(body)
        if problem:
            return problem
        try:
            name = github.normalize_login(body.get("login"))
        except ValueError as error:
            return jsonify(error=str(error)), 400
        try:
            account = github.lookup_user(name)
        except github.GitHubError as error:
            return jsonify(error=str(error)), 502
        if not account:
            return jsonify(error=f"Fant ingen GitHub-bruker som heter «{name}»."), 404
        try:
            github.add_user(account, _added_by())
        except ValueError as error:
            return jsonify(error=str(error)), 409
        g.db.commit()
        return jsonify(github_status()), 201

    @app.delete("/api/settings/github/users/<int:user_id>")
    def remove_github_user(user_id):
        problem = _authorize_access_change(request.get_json(silent=True) or {})
        if problem:
            return problem
        if not github.remove_user(user_id):
            return jsonify(error="Brukeren har ikke tilgang."), 404
        g.db.commit()
        return jsonify(github_status())
