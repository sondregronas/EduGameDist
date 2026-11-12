"""Sign-in with GitHub for admin: the OAuth app credentials and the GitHub users that may sign in.

Everything is stored as settings rows, so it is managed under Settings in admin. The client secret is
write-only: it is never sent back to the browser, only a short hint of how it ends.
"""
import json
import re
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

import settings

CLIENT_ID = "github_client_id"
CLIENT_SECRET = "github_client_secret"
USERS = "github_users"
MAX_USERS = 100
USER_AGENT = "EduGameDist/2.0"
AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
API_URL = "https://api.github.com"
CALLBACK_PATH = "/login/github/callback"
# GitHub user names: letters, digits and single hyphens, not at the start or end, at most 39 characters.
LOGIN_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}")
CREDENTIAL_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,200}")
TOKEN_ERRORS = {
    "incorrect_client_credentials": "GitHub godtok ikke Client ID eller Client secret. Lag en ny hemmelighet i GitHub-appen og lagre den under Innstillinger.",
    "redirect_uri_mismatch": f"Callback-adressen i GitHub-appen stemmer ikke. Den må slutte på {CALLBACK_PATH}.",
    "bad_verification_code": "Koden fra GitHub var utløpt eller allerede brukt. Prøv igjen.",
}


class GitHubError(Exception):
    """GitHub could not be reached, or answered with an error. The message can be shown to the admin."""


def _request(url, data=None, token=None, timeout=10):
    """Send a request to GitHub and return (status, decoded JSON). Tests replace this function."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if token:
        headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    body = urlencode(data).encode("ascii") if data is not None else None
    try:
        with urlopen(Request(url, data=body, headers=headers), timeout=timeout) as response:
            return response.status, json.loads(response.read(1_000_000).decode("utf-8"))
    except HTTPError as error:
        try:
            payload = json.loads(error.read(100_000).decode("utf-8"))
        except ValueError:
            payload = {}
        return error.code, payload
    except (URLError, TimeoutError, OSError, ValueError) as error:
        raise GitHubError("Fikk ikke kontakt med GitHub.") from error


def client_id():
    return settings.get(CLIENT_ID)


def client_secret():
    return settings.get(CLIENT_SECRET)


def configured():
    return bool(client_id() and client_secret())


def active():
    """GitHub sign-in is on when the OAuth app is set up and at least one user may sign in."""
    return configured() and bool(users())


def secret_hint():
    secret = client_secret()
    return f"••••{secret[-4:]}" if secret else ""


def users():
    try:
        stored = json.loads(settings.get(USERS) or "[]")
    except ValueError:
        return []
    return [
        {
            "id": entry["id"],
            "login": str(entry.get("login") or entry["id"]),
            "added_by": str(entry.get("added_by") or ""),
            "added_at": str(entry.get("added_at") or ""),
        }
        for entry in (stored if isinstance(stored, list) else [])
        if isinstance(entry, dict) and isinstance(entry.get("id"), int) and not isinstance(entry.get("id"), bool)
    ]


def save_users(entries):
    settings.put({USERS: json.dumps(entries, ensure_ascii=False) if entries else None})


def find_user(user_id):
    """The allowed user with this GitHub id. Users are matched by id, since names can be changed and reused."""
    if not isinstance(user_id, int) or isinstance(user_id, bool):
        return None
    return next((entry for entry in users() if entry["id"] == user_id), None)


def add_user(account, added_by):
    entries = users()
    if any(entry["id"] == account["id"] for entry in entries):
        raise ValueError(f"@{account['login']} har allerede tilgang.")
    if len(entries) >= MAX_USERS:
        raise ValueError(f"Det kan være maks {MAX_USERS} GitHub-brukere.")
    entries.append({
        "id": account["id"],
        "login": account["login"],
        "added_by": added_by,
        "added_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    save_users(entries)


def remove_user(user_id):
    entries = users()
    remaining = [entry for entry in entries if entry["id"] != user_id]
    if len(remaining) == len(entries):
        return False
    save_users(remaining)
    return True


def refresh_login(account):
    """Keep the shown name up to date when a user has renamed their GitHub account."""
    entries = users()
    for entry in entries:
        if entry["id"] == account["id"] and entry["login"] != account["login"]:
            entry["login"] = account["login"]
            save_users(entries)
            return


def normalize_login(value):
    """Accept "name", "@name" or a profile link such as https://github.com/name."""
    value = str(value or "").strip()
    parsed = urlparse(value if "://" in value else "")
    if parsed.hostname in ("github.com", "www.github.com"):
        value = parsed.path.strip("/").split("/")[0]
    value = value.removeprefix("@")
    if not LOGIN_PATTERN.fullmatch(value):
        raise ValueError("Skriv inn et gyldig GitHub-brukernavn.")
    return value


def validated_credentials(body):
    """The OAuth app settings in the request. The secret may be left out to keep the saved one."""
    values = {}
    identifier = str(body.get("client_id") or "").strip()
    if not CREDENTIAL_PATTERN.fullmatch(identifier):
        raise ValueError("Lim inn Client ID fra GitHub-appen.")
    values[CLIENT_ID] = identifier
    secret = str(body.get("client_secret") or "").strip()
    if secret:
        if not CREDENTIAL_PATTERN.fullmatch(secret):
            raise ValueError("Client secret ser ikke riktig ut. Lim inn hele hemmeligheten fra GitHub.")
        values[CLIENT_SECRET] = secret
    elif not client_secret():
        raise ValueError("Lim inn Client secret fra GitHub-appen.")
    return values


def authorize_url(state):
    # No scope: signing in only needs the user's public profile.
    return f"{AUTHORIZE_URL}?{urlencode({'client_id': client_id(), 'state': state, 'allow_signup': 'false'})}"


def _account(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("id"), int) or not isinstance(payload.get("login"), str):
        raise GitHubError("GitHub sendte et ugyldig svar.")
    return {"id": payload["id"], "login": payload["login"], "type": payload.get("type", "User")}


def sign_in(code):
    """Trade the code from GitHub's redirect for the signed-in account. The token is not kept."""
    _status, payload = _request(TOKEN_URL, data={"client_id": client_id(), "client_secret": client_secret(), "code": code})
    token = payload.get("access_token") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token:
        error = payload.get("error") if isinstance(payload, dict) else None
        raise GitHubError(TOKEN_ERRORS.get(error, "GitHub godtok ikke innloggingen."))
    status, payload = _request(f"{API_URL}/user", token=token)
    if status != 200:
        raise GitHubError("Klarte ikke å hente GitHub-brukeren.")
    return _account(payload)


def lookup_user(login):
    """Find a GitHub user by name. Returns None if there is no such user."""
    status, payload = _request(f"{API_URL}/users/{quote(login)}")
    if status == 404:
        return None
    if status != 200:
        raise GitHubError("Klarte ikke å slå opp brukeren hos GitHub akkurat nå.")
    account = _account(payload)
    return account if account["type"] == "User" else None
