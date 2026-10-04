import errno
import html
import ipaddress
import json
import mimetypes
import os
import re
import shutil
import socket
import sys
import time
import uuid
import zlib
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from flask import (
    Flask,
    abort,
    current_app,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
)
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from werkzeug.exceptions import RequestEntityTooLarge

from database import (
    Game,
    GameCategory,
    GameFile,
    GameStoreLink,
    PLATFORMS,
    all_category_names,
    file_href,
    get_game,
    initialize_db,
    list_games,
    make_engine,
    unique_slug,
)
import settings
from auth import auth_enabled, configure_auth, logged_in, password_status
from pages import PAGES
from richtext import page_sections, rich_text
from stores import FetchError, discover_store_links, steam_search, store_catalog, store_info


ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"
USER_AGENT = "EduGameDist/2.0"
UPLOAD_READ_SIZE = 8 * 1024 * 1024
MAX_JSON_BYTES = 5 * 1024 * 1024
MAX_COVER_BYTES = 25 * 1024 * 1024
MAX_LOGO_BYTES = 2 * 1024 * 1024
STALE_TEMP_SECONDS = 24 * 60 * 60
COVER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
FILE_PLATFORMS = ("windows", "mac", "linux", "android")
UPLOAD_PLATFORMS = FILE_PLATFORMS + ("cover",)
# Game files are stored as <GAMES_DIR>/<folder>/<slug>/<file name>.
PLATFORM_DIRS = {
    "windows": "Windows",
    "mac": "Mac",
    "linux": "Linux",
    "android": "Android",
}
WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{n}" for n in range(1, 10)), *(f"LPT{n}" for n in range(1, 10))}
TEXT_FIELDS = {
    "description": ("Beskrivelsen", 200_000),
    "note": ("Lærernotatet", 200_000),
    "time": ("Spilletiden", 500),
    "players": ("Spillerantallet", 100),
    "developer": ("Utviklernavnet", 500),
}
URL_FIELDS = {
    "developer_link": ("Utviklerlenke", False, 2000),
    "browser_url": ("Nettleserlenke", True, 4000),
    "cover_url": ("Omslagsbildelenke", True, 4000),
}


def _data_dir(value=None):
    return Path(value or os.environ.get("DATA_DIR", ROOT / "data")).resolve()


def _games_dir(value=None):
    return Path(value or os.environ.get("GAMES_DIR", PUBLIC_DIR / "games")).resolve()


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


_OPENER = build_opener(_NoRedirect)


TRUSTED_IMAGE_HOSTS = ("steamstatic.com", "akamaihd.net")


def _is_trusted_host(host):
    host = host.lower().rstrip(".")
    return any(host == suffix or host.endswith("." + suffix) for suffix in TRUSTED_IMAGE_HOSTS)


def _require_public_host(host, port):
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
    except OSError:
        raise FetchError("Fant ikke tjeneren.")
    if not addresses:
        raise FetchError("Fant ikke tjeneren.")
    # Steam's CDN is often answered by a local cache (private address) on school networks.
    if _is_trusted_host(host):
        return
    if not all(ipaddress.ip_address(address.split("%")[0]).is_global for address in addresses):
        raise FetchError("Adressen er ikke tillatt.")


def _fetch(url, max_bytes=2_000_000, timeout=12, accept="*/*"):
    """Fetch a public http(s) URL, following redirects manually so every hop is checked."""
    for _hop in range(5):
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise FetchError("Ugyldig lenke.")
        _require_public_host(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
        call = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
        try:
            with _OPENER.open(call, timeout=timeout) as response:
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise FetchError("Svaret er for stort.")
                return data, response.headers.get_content_type()
        except HTTPError as error:
            location = error.headers.get("Location") if error.code in (301, 302, 303, 307, 308) else None
            if not location:
                raise FetchError(f"HTTP {error.code}")
            url = urljoin(url, location)
        except (URLError, TimeoutError, OSError, ValueError) as error:
            raise FetchError(str(error))
    raise FetchError("For mange videresendinger.")


def _fetch_json(url):
    data, _content_type = _fetch(url, accept="application/json")
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise FetchError("Ugyldig svar.")


def _human_size(size):
    if size is None:
        return ""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1000 or unit == "GB":
            break
        value /= 1000
    if value >= 1000:
        unit, value = "TB", value / 1000
    text = f"{value:.0f}" if unit == "B" or value >= 100 else f"{value:.1f}"
    return f"{text.replace('.', ',')} {unit}"


def _stored_path(stored_name):
    """Where a file lives: games/<Folder>/<slug>/<name> in the game folder, legacy/<platform>/<name> for
    files placed there by hand in older versions, and anything else (covers) in the upload folder."""
    if not stored_name:
        return None
    parts = PurePosixPath(stored_name).parts
    games = Path(current_app.config["GAMES_DIR"])
    if parts[0] == "games":
        if len(parts) != 4 or parts[1] not in PLATFORM_DIRS.values() or ".." in parts:
            return None
        return games.joinpath(*parts[1:])
    if parts[0] == "legacy":
        if len(parts) != 3 or parts[1] not in PLATFORM_DIRS or parts[2] == "..":
            return None
        return games / PLATFORM_DIRS[parts[1]] / parts[2]
    return Path(current_app.config["UPLOAD_DIR"]) / Path(stored_name).name


def _games_folder(platform):
    """The folder for a platform's game files, or None if files written there would be lost when the
    container is replaced (the Docker image requires the folder to be a mounted volume)."""
    folder = Path(current_app.config["GAMES_DIR"]) / PLATFORM_DIRS[platform]
    if current_app.config["GAMES_MOUNT_REQUIRED"] and not (os.path.ismount(folder.parent) or os.path.ismount(folder)):
        return None
    return folder


def _games_name(path):
    return "games/" + path.relative_to(current_app.config["GAMES_DIR"]).as_posix()


def _safe_filename(name, limit=200):
    """A file name that works on Linux and Windows and leaves room for a " (2)" suffix."""
    name = re.sub(r'[\x00-\x1f\x7f<>:"/\\|?*]', "_", name).strip(" .")
    stem, suffix = os.path.splitext(name)
    if len(suffix.encode("utf-8")) > 20:
        stem, suffix = stem + suffix, ""
    if stem.upper() in WINDOWS_RESERVED_NAMES:
        stem = "_" + stem
    if len((stem + suffix).encode("utf-8")) > limit:
        while len((stem + suffix).encode("utf-8")) > limit:
            stem = stem[:-1]
        stem = stem.rstrip(" .")
    return (stem or "fil") + suffix


def _name_variants(name):
    stem, suffix = os.path.splitext(name)
    yield name
    for number in range(2, 1000):
        yield f"{stem} ({number}){suffix}"


def _move_exclusive(source, target):
    """Move `source` to `target`, raising FileExistsError instead of overwriting another file."""
    os.close(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL))
    try:
        os.replace(source, target)
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def _first_free(directory, name, place):
    for candidate in _name_variants(name):
        target = directory / candidate
        try:
            place(target)
            return target
        except FileExistsError:
            continue
    raise FileExistsError(errno.EEXIST, "No free file name", str(directory / name))


def _place_file(source, directory, name, keep_source=False):
    """Move `source` into `directory` under the first free variant of `name` and return the new path.

    Across filesystems (and with keep_source) the file is copied instead and the source is left in
    place, so the caller can delete it once the database points at the new path."""
    directory.mkdir(parents=True, exist_ok=True)
    if not keep_source:
        try:
            return _first_free(directory, name, lambda target: _move_exclusive(source, target))
        except OSError as error:
            if error.errno != errno.EXDEV:
                raise
    staged = directory / f".{uuid.uuid4().hex}.part"
    try:
        shutil.copyfile(source, staged)
        return _first_free(directory, name, lambda target: _move_exclusive(staged, target))
    finally:
        staged.unlink(missing_ok=True)


def _remove_if_empty(directory):
    """Remove a game's folder (<GAMES_DIR>/<Folder>/<slug>) once its last file is gone."""
    if directory.parent.parent != Path(current_app.config["GAMES_DIR"]):
        return
    try:
        directory.rmdir()
    except OSError:
        pass


def _relocate_game_files(session, game):
    """Move a game's files into <GAMES_DIR>/<Folder>/<slug>/: after a rename, and for files stored by
    older versions (random names in the upload folder, or loose files in the platform folder)."""
    moved = 0
    items = session.scalars(
        select(GameFile).where(
            GameFile.game_id == game.id,
            GameFile.platform.in_(FILE_PLATFORMS),
            GameFile.stored_name.is_not(None),
        )
    ).all()
    for item in items:
        folder = _games_folder(item.platform)
        source = _stored_path(item.stored_name)
        if not folder or not source or source.parent == folder / game.slug or not source.is_file():
            continue
        old_name = item.stored_name
        name = source.name if old_name.startswith(("games/", "legacy/")) else _safe_filename(item.original_name)
        # A hand-placed legacy file can belong to several games; each of them gets its own copy.
        shared = session.scalar(
            select(GameFile.id).where(GameFile.stored_name == old_name, GameFile.id != item.id).limit(1)
        ) is not None
        try:
            target = _place_file(source, folder / game.slug, name, keep_source=shared)
        except OSError as error:
            current_app.logger.warning("Could not move %s into %s: %s", source, folder / game.slug, error)
            continue
        item.stored_name = _games_name(target)
        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            if source.exists():
                target.unlink(missing_ok=True)
            else:
                os.replace(target, source)
            raise
        if not shared:
            source.unlink(missing_ok=True)
            if old_name.startswith("games/"):
                _remove_if_empty(source.parent)
        moved += 1
    return moved


@contextmanager
def _exclusive_lock(path):
    """Let one worker process at a time move files. A no-op where fcntl is missing (Windows)."""
    try:
        import fcntl
    except ImportError:
        yield
        return
    with open(path, "a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _migrate_game_files(app):
    with app.app_context():
        unavailable = [PLATFORM_DIRS[platform] for platform in FILE_PLATFORMS if not _games_folder(platform)]
        if unavailable:
            app.logger.warning(
                "%s is not a mounted volume, so new %s files are kept in %s. Mount ./games at %s "
                "in docker-compose.yml to store them as <Platform>/<game>/<file>.",
                app.config["GAMES_DIR"], ", ".join(unavailable), app.config["UPLOAD_DIR"], app.config["GAMES_DIR"],
            )
        with _exclusive_lock(Path(app.config["DATA_DIR"]) / ".file-migration.lock"), \
                Session(app.extensions["database_engine"]) as session:
            game_ids = session.scalars(
                select(GameFile.game_id)
                .where(GameFile.platform.in_(FILE_PLATFORMS), GameFile.stored_name.is_not(None))
                .distinct()
            ).all()
            games = [session.get(Game, game_id) for game_id in game_ids]
            moved = sum(_relocate_game_files(session, game) for game in games if game)
        if moved:
            print(f"Moved {moved} game file(s) into per-game folders in {app.config['GAMES_DIR']}.", flush=True)


def _decorate_files(game):
    for item in game["files"]:
        path = _stored_path(item["stored_name"])
        try:
            size = path.stat().st_size if path else None
        except OSError:
            size = None
        item["size"] = size
        item["size_text"] = _human_size(size)
        del item["stored_name"]
    return game


def _file_view(item):
    return {key: value for key, value in item.items() if key != "stored_name"}


def _open_app(mode, data_dir=None, games_dir=None):
    data = _data_dir(data_dir)
    data.mkdir(parents=True, exist_ok=True)
    app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=None)
    app.config.update(
        APP_MODE=mode,
        DATA_DIR=str(data),
        DATABASE_PATH=str(data / "gamedb.db"),
        UPLOAD_DIR=str(data / "uploads"),
        TEMP_DIR=str(data / "upload-tmp"),
        LEGACY_COVER_DIR=str(data / "legacy-covers"),
        SITE_DIR=str(data / "site"),
        GAMES_DIR=str(_games_dir(games_dir)),
        GAMES_MOUNT_REQUIRED=os.environ.get("GAMES_MOUNT_REQUIRED", "").lower() in ("1", "true", "yes"),
        TITLE=os.environ.get("TITLE", "Spilldistribusjon"),
        PUBLIC_URL=os.environ.get("PUBLIC_URL", "http://localhost/"),
    )
    if mode == "public" and not Path(app.config["DATABASE_PATH"]).is_file():
        raise RuntimeError("Start the admin app once to initialize the shared database.")
    engine = make_engine(app.config["DATABASE_PATH"], read_only=mode == "public")
    if mode == "admin":
        initialize_db(engine)
    app.extensions["database_engine"] = engine
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    if mode == "admin":
        _cleanup_temp_files(Path(app.config["TEMP_DIR"]))
        for folder in PLATFORM_DIRS.values():
            temp_dir = Path(app.config["GAMES_DIR"]) / folder / ".upload-tmp"
            if temp_dir.is_dir():
                _cleanup_temp_files(temp_dir)

    @app.before_request
    def open_database():
        g.db = Session(current_app.extensions["database_engine"])

    @app.teardown_appcontext
    def close_database(error=None):
        session = g.pop("db", None)
        if session is not None:
            if error is None:
                session.commit()
            else:
                session.rollback()
            session.close()

    app.jinja_env.filters["rich_text"] = rich_text
    app.jinja_env.filters["hue"] = lambda value: zlib.crc32(str(value).encode("utf-8")) % 360

    @app.context_processor
    def template_context():
        return {
            "admin": mode == "admin",
            "site": settings.site(),
            "public_url": current_app.config["PUBLIC_URL"],
            "auth_enabled": mode == "admin" and auth_enabled(),
            "logged_in": mode == "admin" and logged_in(),
        }

    @app.get("/assets/<path:asset>")
    def assets(asset):
        # Game files live under public/games in the Docker image; they are only served through
        # /<slug>/files/<id>, which hides files of hidden games.
        if PurePosixPath(asset).parts[0].lower() == "games":
            abort(404)
        return send_from_directory(PUBLIC_DIR, asset)

    @app.get("/favicon.ico")
    def favicon():
        logo = settings.site()["logo"]
        if logo:
            return redirect(f"/logo/{logo}")
        return send_from_directory(PUBLIC_DIR / "img", "favicon.ico", max_age=86400)

    @app.get("/logo/<name>")
    def site_logo(name):
        path = Path(current_app.config["SITE_DIR"]) / name
        if name != settings.site()["logo"] or Path(name).name != name or not path.is_file():
            abort(404)
        response = send_file(
            path,
            mimetype=mimetypes.guess_type(name)[0] or "application/octet-stream",
            max_age=365 * 24 * 60 * 60,
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/legacy-covers/<path:filename>")
    def legacy_cover(filename):
        if (
            Path(filename).name != filename
            or Path(filename).suffix.lower() not in COVER_EXTENSIONS
        ):
            abort(404)
        path = Path(current_app.config["LEGACY_COVER_DIR"]) / filename
        response = send_file(path, mimetype=mimetypes.guess_type(filename)[0] or "application/octet-stream")
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/files/<int:file_id>")
    def get_file_legacy_url(file_id):
        item = g.db.get(GameFile, file_id)
        game = item and g.db.get(Game, item.game_id)
        if not game:
            abort(404)
        return redirect(file_href(game.slug, file_id), code=301)

    @app.get("/<slug>/files/<int:file_id>")
    def get_file(slug, file_id):
        item = g.db.get(GameFile, file_id)
        game = item and g.db.get(Game, item.game_id)
        if not item or not item.stored_name or not game or game.slug != slug or (game.hidden and mode == "public"):
            abort(404)
        path = _stored_path(item.stored_name)
        if not path or not path.is_file():
            abort(404)
        is_cover = item.platform == "cover"
        response = send_file(
            path,
            mimetype=mimetypes.guess_type(item.original_name)[0] if is_cover else None,
            as_attachment=not is_cover,
            download_name=item.original_name,
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        if is_cover:
            response.headers["Cache-Control"] = "public, max-age=86400"
        return response

    @app.get("/health")
    def health():
        g.db.scalar(select(Game.id).limit(1))
        return jsonify(status="ok")

    @app.get("/")
    def index():
        games = list_games(g.db, include_hidden=mode == "admin")
        categories = {}
        for game in games:
            for name in game["category"]:
                categories.setdefault(name.lower(), [name, 0])[1] += 1
        present = {platform for game in games for platform in game["platforms"]}
        return render_template(
            "index.html",
            games=games,
            categories=sorted(categories.values(), key=lambda entry: entry[0].lower()),
            platforms=[(key, label) for key, label in PLATFORMS.items() if key in present],
            remote_covers=sum(1 for game in games if _is_remote(game["cover"])) if mode == "admin" else 0,
            storage_warning=mode == "admin" and any(_games_folder(platform) is None for platform in FILE_PLATFORMS),
        )

    def editable_page(name):
        page = PAGES[name]
        return render_template(
            "page.html",
            title=page["title"],
            page=page_sections(settings.page_content(name)),
            page_name=name,
            default_icon=page["icon"],
        )

    @app.get("/install")
    def installation_guide():
        return editable_page("install")

    @app.get("/vilkar")
    def terms():
        return editable_page("terms")

    @app.get("/<slug>")
    def game_page(slug):
        query = select(Game.id).where(Game.slug == slug)
        if mode == "public":
            query = query.where(Game.hidden.is_(False))
        game_id = g.db.scalar(query)
        if not game_id:
            abort(404)
        game = _decorate_files(get_game(g.db, game_id))
        context = {"title": game["title"], "game": game}
        if mode == "admin":
            context["editor"] = {
                "game": _client_game(game),
                "stores": store_catalog(),
                "categories": all_category_names(g.db),
            }
            context["upload_platforms"] = {key: PLATFORMS[key] for key in FILE_PLATFORMS}
        return render_template("game.html", **context)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html", title="Ikke funnet"), 404

    if mode == "admin":
        _configure_admin(app)
        _migrate_game_files(app)
    return app


def create_public_app(data_dir=None, games_dir=None):
    return _open_app("public", data_dir, games_dir)


def create_admin_app(data_dir=None, games_dir=None):
    return _open_app("admin", data_dir, games_dir)


def _cleanup_temp_files(directory):
    directory.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - STALE_TEMP_SECONDS
    for path in directory.iterdir():
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            continue


def _is_remote(url):
    parsed = urlparse(url or "")
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _client_game(game):
    cover = game["cover"]
    return {
        "id": game["id"],
        "slug": game["slug"],
        "title": game["title"],
        "description": game["description"],
        "note": game["note"],
        "players": game["players"],
        "time": game["ttb"],
        "developer": game["developer"],
        "developer_link": game["developer_link"],
        "browser_url": game["browser_url"],
        "steam_app_id": game["steam_app_id"],
        "cover_url": "" if cover.startswith("data:") else cover,
        "categories": game["category"],
        "links": game["links"],
        "hidden": game["hidden"],
        "files": [_file_view(item) for item in game["files"]],
    }


def _configure_admin(app):
    configure_auth(app, Path(app.config["DATABASE_PATH"]).parent)

    @app.after_request
    def admin_security_headers(response):
        if response.mimetype in ("text/html", "application/json"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.before_request
    def guard_requests():
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return None
        origin = request.headers.get("Origin")
        fetch_site = request.headers.get("Sec-Fetch-Site")
        if origin and urlparse(origin).netloc.lower() != request.host.lower():
            return jsonify(error="Endringer fra andre nettsteder er ikke tillatt."), 403
        if fetch_site and fetch_site != "same-origin":
            return jsonify(error="Endringer fra andre nettsteder er ikke tillatt."), 403
        if (
            request.endpoint != "upload_file"
            and request.content_length is not None
            and request.content_length > MAX_JSON_BYTES
        ):
            return jsonify(error="Forespørselen er for stor."), 413
        return None

    @app.get("/settings")
    def settings_page():
        return render_template(
            "settings.html",
            title="Innstillinger",
            data=settings.editor_data(),
            pages=PAGES,
            default_title=current_app.config["TITLE"],
            password=password_status(),
        )

    @app.put("/api/settings")
    def update_settings():
        try:
            values = settings.validate(request.get_json(silent=True) or {})
        except ValueError as error:
            return jsonify(error=str(error)), 400
        settings.put(values)
        return jsonify(status="saved")

    @app.post("/api/settings/logo")
    def upload_logo():
        declared = request.content_length
        if not declared:
            return jsonify(error="Filen er tom."), 400
        if declared > MAX_LOGO_BYTES:
            return jsonify(error="Logoen er for stor (maks 2 MB)."), 413
        data = request.get_data(cache=False)
        extension = _sniff_image(data) or (".ico" if data.startswith(b"\x00\x00\x01\x00") else None)
        if not extension:
            return jsonify(error="Logoen må være et PNG-, JPEG-, WebP-, GIF- eller ICO-bilde."), 400
        directory = Path(current_app.config["SITE_DIR"])
        name = f"logo-{uuid.uuid4().hex[:12]}{extension}"
        try:
            directory.mkdir(parents=True, exist_ok=True)
            (directory / name).write_bytes(data)
        except OSError:
            return jsonify(error="Kunne ikke lagre logoen på tjeneren."), 500
        old = settings.get("logo")
        settings.put({"logo": name})
        g.db.commit()
        _remove_logo(old)
        return jsonify(logo_url=f"/logo/{name}")

    @app.delete("/api/settings/logo")
    def delete_logo():
        old = settings.get("logo")
        settings.put({"logo": None})
        g.db.commit()
        _remove_logo(old)
        return jsonify(logo_url="")

    @app.get("/api/games")
    def admin_games():
        return jsonify([_client_game(_decorate_files(game)) for game in list_games(g.db)])

    @app.get("/api/games/<int:game_id>")
    def admin_game(game_id):
        game = get_game(g.db, game_id)
        if not game:
            return jsonify(error="Spillet finnes ikke."), 404
        return jsonify(_client_game(_decorate_files(game)))

    @app.post("/api/games")
    def create_game():
        values = _validated_game_values(request.get_json(silent=True) or {}, creating=True)
        if isinstance(values, tuple):
            return values
        game = Game(title=values["title"], slug=unique_slug(g.db, values["title"]))
        g.db.add(game)
        g.db.flush()
        warning = _apply_values(game, values)
        return jsonify(id=game.id, slug=game.slug, warning=warning), 201

    @app.put("/api/games/<int:game_id>")
    def update_game(game_id):
        game = g.db.get(Game, game_id)
        if not game:
            return jsonify(error="Spillet finnes ikke."), 404
        values = _validated_game_values(request.get_json(silent=True) or {})
        if isinstance(values, tuple):
            return values
        old_slug = game.slug
        if "title" in values and values["title"] != game.title:
            game.slug = unique_slug(g.db, values["title"], exclude_id=game_id)
        warning = _apply_values(game, values)
        if game.slug != old_slug:
            g.db.commit()
            _relocate_game_files(g.db, game)
        return jsonify(id=game_id, slug=game.slug, warning=warning)

    @app.delete("/api/games/<int:game_id>")
    def delete_game(game_id):
        game = g.db.get(Game, game_id)
        if not game:
            return jsonify(error="Spillet finnes ikke."), 404
        files = g.db.scalars(select(GameFile).where(GameFile.game_id == game_id)).all()
        stored_names = [item.stored_name for item in files]
        g.db.delete(game)
        g.db.commit()
        for stored_name in stored_names:
            _delete_uploaded_file(stored_name)
        return jsonify(status="deleted")

    @app.post("/api/steam")
    def steam_metadata():
        term = str((request.get_json(silent=True) or {}).get("steam", "")).strip()
        if not term:
            return jsonify(error="Skriv inn en Steam-lenke, en app-ID eller navnet på spillet."), 400
        app_id = _steam_app_id(term)
        if not app_id and ("://" in term or "/" in term):
            return jsonify(error="Dette ser ikke ut som en lenke til Steam-butikken."), 400
        if not app_id:
            try:
                app_id = steam_search(term, _fetch)
            except FetchError:
                return jsonify(error="Klarte ikke å søke på Steam akkurat nå."), 502
            if not app_id:
                return jsonify(error=f"Fant ingen eksakt treff på «{term}» på Steam. Lim inn lenken til Steam-siden i stedet."), 404
        try:
            payload = _fetch_json(
                f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=norwegian"
            )
        except FetchError:
            return jsonify(error="Klarte ikke å hente informasjon fra Steam akkurat nå."), 502
        result = payload.get(str(app_id)) if isinstance(payload, dict) else None
        if not isinstance(result, dict) or not result.get("success") or not isinstance(result.get("data"), dict):
            return jsonify(error="Steam fant ikke et spill med denne app-ID-en."), 404
        data = result["data"]
        description = re.sub(r"<[^>]*>", " ", str(data.get("short_description") or ""))
        description = re.sub(r"\s+", " ", html.unescape(description)).strip()
        developers = data.get("developers")
        if not isinstance(developers, list):
            developers = []
        return jsonify(
            title=str(data.get("name") or ""),
            description=description,
            cover_url=str(data.get("header_image") or "").split("?")[0],
            developer=str(developers[0]) if developers else "",
            developer_link=_developer_website(data),
            steam_app_id=str(app_id),
            store_links=[{"url": f"https://store.steampowered.com/app/{app_id}/", **store_info("https://store.steampowered.com/")}],
        )

    @app.post("/api/stores")
    def find_stores():
        body = request.get_json(silent=True) or {}
        title = str(body.get("title", "")).strip()
        if not title or len(title) > 250:
            return jsonify(error="Skriv inn en tittel først."), 400
        links = discover_store_links(title, _fetch, developer=str(body.get("developer", ""))[:500])
        return jsonify(links=links)

    @app.post("/api/covers/localize")
    def localize_covers():
        done = failed = 0
        reason = ""
        for game in g.db.scalars(select(Game)).all():
            if not _is_remote(game.cover_url):
                continue
            warning = _localize_cover(game)
            if warning is None:
                done += 1
            else:
                failed += 1
                reason = reason or warning
        return jsonify(downloaded=done, failed=failed, reason=reason)

    @app.post("/api/games/<int:game_id>/files")
    def upload_file(game_id):
        game = g.db.get(Game, game_id)
        if not game:
            return jsonify(error="Spillet finnes ikke."), 404
        platform = request.headers.get("X-Platform", "")
        if platform not in UPLOAD_PLATFORMS:
            return jsonify(error="Ugyldig plattform."), 400
        file_name = unquote(request.headers.get("X-File-Name", ""))
        file_name = "".join(
            character for character in file_name.replace("\\", "/").split("/")[-1].strip()
            if character.isprintable()
        )
        if not file_name or len(file_name) > 255:
            return jsonify(error="Ugyldig filnavn."), 400
        if platform == "cover" and Path(file_name).suffix.lower() not in COVER_EXTENSIONS:
            return jsonify(error="Omslagsbilder må være PNG-, JPEG-, WebP- eller GIF-filer."), 400
        declared = request.content_length
        if declared is None:
            return jsonify(error="Opplastingen mangler Content-Length."), 411
        if declared == 0:
            return jsonify(error="Filen er tom."), 400
        if platform == "cover" and declared > MAX_COVER_BYTES:
            return jsonify(error="Omslagsbildet er for stort (maks 25 MB)."), 413

        # Game files go to <GAMES_DIR>/<Platform>/<slug>/ under their own name. Covers (and game files when
        # the game folder is not a mounted volume) get a random name in the upload folder.
        folder = _games_folder(platform) if platform != "cover" else None
        temp_dir = folder / ".upload-tmp" if folder else Path(current_app.config["TEMP_DIR"])
        temp_path = temp_dir / f"{uuid.uuid4().hex}.part"
        received = 0
        try:
            temp_dir.mkdir(parents=True, exist_ok=True)
            with temp_path.open("wb") as stream:
                while True:
                    block = request.stream.read(UPLOAD_READ_SIZE)
                    if not block:
                        break
                    received += len(block)
                    if received > declared:
                        break
                    stream.write(block)
            if received != declared:
                temp_path.unlink(missing_ok=True)
                return jsonify(error="Opplastingen ble avbrutt før hele filen var mottatt."), 400
            if folder:
                final_path = _place_file(temp_path, folder / game.slug, _safe_filename(file_name))
                stored_name = _games_name(final_path)
            else:
                suffix = Path(file_name).suffix.lower()
                stored_name = uuid.uuid4().hex + (suffix if re.fullmatch(r"\.[a-z0-9]{1,10}", suffix) else "")
                final_path = Path(current_app.config["UPLOAD_DIR"]) / stored_name
                final_path.parent.mkdir(parents=True, exist_ok=True)
                os.replace(temp_path, final_path)
        except OSError as error:
            temp_path.unlink(missing_ok=True)
            if error.errno == errno.ENOSPC:
                return jsonify(error="Det er ikke nok diskplass på tjeneren."), 507
            return jsonify(error="Kunne ikke lagre filen på tjeneren."), 500
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise

        try:
            item = GameFile(game_id=game_id, platform=platform, original_name=file_name, stored_name=stored_name)
            g.db.add(item)
            g.db.flush()
            if platform == "cover":
                _replace_cover(game, item)
            g.db.commit()
        except SQLAlchemyError:
            _delete_uploaded_file(stored_name)
            raise
        return jsonify(
            id=item.id,
            href=file_href(game.slug, item.id),
            name=file_name,
            platform=platform,
            size=received,
            size_text=_human_size(received),
        ), 201

    @app.delete("/api/files/<int:file_id>")
    def delete_file(file_id):
        item = g.db.get(GameFile, file_id)
        if not item:
            return jsonify(error="Filen finnes ikke."), 404
        game = g.db.get(Game, item.game_id)
        if item.platform == "cover" and game and game.cover_url == f"/files/{file_id}":
            game.cover_url = ""
        stored_name = item.stored_name
        g.db.delete(item)
        g.db.commit()
        _delete_uploaded_file(stored_name)
        return jsonify(status="deleted")

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_error):
        return jsonify(error="Forespørselen var for stor."), 413


def _delete_uploaded_file(stored_name):
    # Files that older versions expected to be managed by hand are left alone.
    if not stored_name or stored_name.startswith("legacy/"):
        return
    path = _stored_path(stored_name)
    if not path:
        return
    path.unlink(missing_ok=True)
    if stored_name.startswith("games/"):
        _remove_if_empty(path.parent)


def _remove_logo(name):
    if name and Path(name).name == name:
        (Path(current_app.config["SITE_DIR"]) / name).unlink(missing_ok=True)


def _replace_cover(game, item):
    """Make `item` the only cover file of the game and point the game at it."""
    old_names = []
    for other in g.db.scalars(
        select(GameFile).where(GameFile.game_id == game.id, GameFile.platform == "cover", GameFile.id != item.id)
    ).all():
        old_names.append(other.stored_name)
        g.db.delete(other)
    game.cover_url = f"/files/{item.id}"
    g.db.flush()
    for name in old_names:
        _delete_uploaded_file(name)


def _prune_cover_files(game):
    keep = game.cover_url or ""
    for item in g.db.scalars(
        select(GameFile).where(GameFile.game_id == game.id, GameFile.platform == "cover")
    ).all():
        if keep != f"/files/{item.id}":
            _delete_uploaded_file(item.stored_name)
            g.db.delete(item)
    g.db.flush()


def _sniff_image(data):
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    return None


def _localize_cover(game):
    """Download a remote cover into local storage. Returns a warning text on failure."""
    url = game.cover_url
    try:
        data, content_type = _fetch(url, max_bytes=MAX_COVER_BYTES, timeout=20, accept="image/*")
    except FetchError as error:
        return f"Klarte ikke å laste ned omslagsbildet ({error}). Lenken beholdes i stedet."
    extension = IMAGE_TYPES.get(content_type) or _sniff_image(data)
    if not extension or not data:
        return "Lenken pekte ikke på et støttet bilde. Lenken beholdes i stedet."
    stored_name = uuid.uuid4().hex + extension
    path = Path(current_app.config["UPLOAD_DIR"]) / stored_name
    try:
        path.write_bytes(data)
    except OSError:
        return "Kunne ikke lagre omslagsbildet på tjeneren."
    name = Path(unquote(urlparse(url).path)).name or "omslag"
    if Path(name).suffix.lower() not in COVER_EXTENSIONS:
        name = Path(name).stem + extension
    item = GameFile(game_id=game.id, platform="cover", original_name=name[:255], stored_name=stored_name)
    g.db.add(item)
    g.db.flush()
    _replace_cover(game, item)
    return None


def _canonical_cover_url(value):
    """Covers are stored as /files/<id>; the public URL /<slug>/files/<id> maps back to that."""
    value = value.split("?")[0] if value.startswith("/") else value
    match = re.fullmatch(r"/[^/]+/files/(\d+)", value)
    return f"/files/{match.group(1)}" if match else value


def _apply_values(game, values):
    for key in ("title", "description", "note", "time", "players", "developer", "developer_link", "browser_url", "steam_app_id", "cover_url", "hidden"):
        if key in values:
            value = values[key]
            if key == "cover_url" and isinstance(value, str):
                value = _canonical_cover_url(value)
            setattr(game, key, value)
    if "categories" in values:
        game.categories.clear()
        g.db.flush()
        game.categories = [
            GameCategory(game_id=game.id, name=name, position=position)
            for position, name in enumerate(values["categories"])
        ]
    if "store_links" in values:
        game.store_links.clear()
        g.db.flush()
        game.store_links = [
            GameStoreLink(game_id=game.id, url=url, label=store_info(url)["label"], position=position)
            for position, url in enumerate(values["store_links"])
        ]
    g.db.flush()
    if "cover_url" not in values:
        return None
    if _is_remote(game.cover_url):
        warning = _localize_cover(game)
        _prune_cover_files(game)
        return warning
    _prune_cover_files(game)
    return None


def _validated_game_values(body, creating=False):
    """Validate the fields that are present in the request. Missing fields are left untouched."""
    values = {}
    try:
        if creating or "title" in body:
            title = str(body.get("title", "")).strip()
            if not title or len(title) > 250:
                raise ValueError("Tittel er påkrevd og kan ikke være lengre enn 250 tegn.")
            values["title"] = title
        for key, (label, limit) in TEXT_FIELDS.items():
            if key in body:
                value = str(body.get(key) or "").strip()
                if len(value) > limit:
                    raise ValueError(f"{label} er for lang.")
                values[key] = value
        for key, (label, allow_local, limit) in URL_FIELDS.items():
            if key in body:
                value = str(body.get(key) or "").strip()
                if len(value) > limit:
                    raise ValueError(f"{label} er for lang.")
                values[key] = _http_or_local_url(value, label) if allow_local else _http_url(value, label)
        if "steam_app_id" in body:
            value = str(body.get("steam_app_id") or "").strip()
            if value and (not value.isascii() or not value.isdigit() or len(value) > 20):
                raise ValueError("Steam-app-ID må bare inneholde sifre.")
            values["steam_app_id"] = value
        if "hidden" in body:
            if not isinstance(body["hidden"], bool):
                raise ValueError("Synlighet må være true eller false.")
            values["hidden"] = body["hidden"]
        if "categories" in body:
            categories = _split_values(body.get("categories"))
            if len(categories) > 30 or any(len(name) > 100 for name in categories):
                raise ValueError("Maks 30 kategorier på maks 100 tegn hver.")
            values["categories"] = categories
        if "store_links" in body:
            links = _split_values(body.get("store_links"))
            if len(links) > 20:
                raise ValueError("Maks 20 butikklenker.")
            values["store_links"] = [_http_url(link, "Butikklenke") for link in links]
    except ValueError as error:
        return jsonify(error=str(error)), 400
    return values


def _split_values(value):
    if isinstance(value, str):
        entries = value.splitlines() if "\n" in value else value.split(",")
    elif isinstance(value, list):
        entries = value
    else:
        entries = []
    return list(dict.fromkeys(str(entry).strip() for entry in entries if str(entry).strip()))


def _http_url(value, label):
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or len(value) > 4000:
        raise ValueError(f"{label} må være en http- eller https-lenke.")
    return value


def _http_or_local_url(value, label):
    if value.startswith("/") and not value.startswith("//"):
        return value
    return _http_url(value, label)


def _developer_website(data):
    for key in ("website", "support_info"):
        value = data.get(key)
        if isinstance(value, dict):
            value = value.get("url")
        if isinstance(value, str):
            value = value.strip()
            parsed = urlparse(value)
            if parsed.scheme in ("http", "https") and parsed.netloc and len(value) <= 2000:
                return value
    return ""


def _steam_app_id(value):
    value = value.strip()
    if value.isascii() and value.isdigit() and len(value) <= 20:
        return value
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in (
        "store.steampowered.com",
        "www.steampowered.com",
    ):
        return None
    match = re.fullmatch(r"/app/([0-9]{1,20})(?:/.*)?", parsed.path)
    return match.group(1) if match else None


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("public", "admin"):
        raise SystemExit("Usage: python app.py public|admin")
    app = create_public_app() if sys.argv[1] == "public" else create_admin_app()
    default_port = "80" if sys.argv[1] == "public" else "8081"
    # Debug (live reload and the interactive debugger) is only for local development.
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", default_port)),
        debug=os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes"),
    )
