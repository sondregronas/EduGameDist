import base64
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    case,
    create_engine,
    event,
    func,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    Session,
    mapped_column,
    relationship,
)

from stores import store_info


PLATFORMS = {
    "browser": "Nettleser",
    "windows": "Windows",
    "mac": "Mac",
    "linux": "Linux",
    "android": "Android",
    "cover": "Omslagsbilde",
}
RESERVED_SLUGS = {"api", "assets", "files", "legacy-covers", "health", "install", "vilkar"}
LEGACY_PLATFORMS = {
    "windows_download": "windows",
    "mac_download": "mac",
    "linux_download": "linux",
    "android_download": "android",
}


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (Index("idx_games_slug", "Slug", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    title: Mapped[str] = mapped_column("Title", String, nullable=False)
    description: Mapped[str | None] = mapped_column("Description", Text, default=None)
    note: Mapped[str | None] = mapped_column("Note", Text, default=None)
    cover: Mapped[str | bytes | None] = mapped_column("Cover", Text, default=None)
    time: Mapped[str | None] = mapped_column("Time", String, default=None)
    players: Mapped[str | None] = mapped_column("Players", String, default=None)
    category1: Mapped[str | None] = mapped_column("Category1", String, default=None)
    category2: Mapped[str | None] = mapped_column("Category2", String, default=None)
    category3: Mapped[str | None] = mapped_column("Category3", String, default=None)
    developer: Mapped[str | None] = mapped_column("Developer", String, default=None)
    developer_link: Mapped[str | None] = mapped_column("Developer_link", String, default=None)
    browser_url: Mapped[str | None] = mapped_column("Url", String, default=None)
    windows_download: Mapped[str | None] = mapped_column("Win_dl", String, default=None)
    mac_download: Mapped[str | None] = mapped_column("Mac_dl", String, default=None)
    linux_download: Mapped[str | None] = mapped_column("Linux_dl", String, default=None)
    android_download: Mapped[str | None] = mapped_column("Android_dl", String, default=None)
    store1: Mapped[str | None] = mapped_column("Store1", String, default=None)
    store2: Mapped[str | None] = mapped_column("Store2", String, default=None)
    store3: Mapped[str | None] = mapped_column("Store3", String, default=None)
    store4: Mapped[str | None] = mapped_column("Store4", String, default=None)
    store5: Mapped[str | None] = mapped_column("Store5", String, default=None)
    cover_url: Mapped[str | None] = mapped_column("CoverUrl", Text, default=None)
    steam_app_id: Mapped[str | None] = mapped_column("SteamAppId", String, default=None)
    slug: Mapped[str | None] = mapped_column("Slug", String, default=None)
    categories: Mapped[list["GameCategory"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        default_factory=list,
        order_by="GameCategory.position",
        repr=False,
    )
    store_links: Mapped[list["GameStoreLink"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        default_factory=list,
        order_by="GameStoreLink.position",
        repr=False,
    )


class GameCategory(Base):
    __tablename__ = "game_categories"
    __table_args__ = (
        UniqueConstraint("game_id", "name", name="uq_game_category_name"),
        Index("idx_game_categories_order", "game_id", "position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    game: Mapped[Game] = relationship(back_populates="categories", init=False, repr=False)


class GameStoreLink(Base):
    __tablename__ = "game_store_links"
    __table_args__ = (Index("idx_game_store_links_order", "game_id", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(String, default="")
    position: Mapped[int] = mapped_column(Integer, default=0)
    game: Mapped[Game] = relationship(back_populates="store_links", init=False, repr=False)


class GameFile(Base):
    __tablename__ = "game_files"
    __table_args__ = (Index("idx_game_files_game_order", "game_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(String, nullable=False)
    original_name: Mapped[str] = mapped_column(String, nullable=False)
    stored_name: Mapped[str | None] = mapped_column(String, default=None)
    url: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        default_factory=lambda: datetime.now(timezone.utc),
        server_default=func.current_timestamp(),
    )


class AppMigration(Base):
    __tablename__ = "app_migrations"

    name: Mapped[str] = mapped_column(String, primary_key=True)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(connection, _record):
    if connection.__class__.__module__ != "sqlite3":
        return
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA busy_timeout = 30000")
    cursor.close()


def make_engine(db_path, read_only=False):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path = str(path)
    engine = create_engine(
        f"sqlite:///{path.replace(chr(92), '/')}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    if read_only:
        @event.listens_for(engine, "connect")
        def _set_read_only(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA query_only = ON")
            cursor.close()
    return engine


def _slugify(value):
    value = value.strip().lower()
    value = re.sub(r"[^\w-]+", "-", value, flags=re.UNICODE)
    return re.sub(r"-+", "-", value).strip("-") or "game"


def _legacy_cover_path(value):
    """Map an old NocoDB attachment path (e.g. /download/noco/Games/Games/Cover/x.jpg) to a legacy cover URL."""
    parsed = urlparse(value)
    path = "/" + unquote(parsed.path).lstrip("/")
    if parsed.netloc and not (path.startswith("/download/") and "/Cover/" in path):
        return ""
    if path.startswith("/download/") or "/Cover/" in path:
        name = Path(path).name
        if Path(name).suffix:
            return "/legacy-covers/" + name
    return ""


def _legacy_cover_url(value):
    if isinstance(value, bytes):
        return "data:image/jpeg;base64," + base64.b64encode(value).decode("ascii")
    if not isinstance(value, str) or not value:
        return ""
    if _is_http_url(value):
        return _legacy_cover_path(value) or value
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return _legacy_cover_path(value)
    try:
        item = parsed[0] if isinstance(parsed, list) and parsed else parsed
        path = item.get("path") or item.get("url", "")
        if _is_http_url(path):
            return _legacy_cover_path(path) or path
        return _legacy_cover_path(path) or (
            "/legacy-covers/" + unquote(Path(path).name) if path else ""
        )
    except (AttributeError, IndexError, TypeError):
        return ""


def _is_http_url(value):
    parsed = urlparse(value or "")
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _public_url(value, allow_local=False):
    if not isinstance(value, str):
        return ""
    if allow_local and value.startswith("/") and not value.startswith("//"):
        return value
    return value if _is_http_url(value) else ""


def _public_cover_url(value):
    if value.startswith("data:image/jpeg;base64,"):
        return value
    return _public_url(value, allow_local=True)


def initialize_db(engine):
    with engine.begin() as connection:
        connection.execute(text("PRAGMA journal_mode = WAL"))
        Base.metadata.create_all(connection)
        columns = {column["name"].lower() for column in inspect(connection).get_columns("games")}
        for column, definition in (("CoverUrl", "TEXT"), ("SteamAppId", "TEXT"), ("Slug", "TEXT")):
            if column.lower() not in columns:
                connection.execute(text(f'ALTER TABLE games ADD COLUMN "{column}" {definition}'))

    with Session(engine) as session:
        used_slugs = set(RESERVED_SLUGS)
        for game in session.scalars(select(Game).order_by(Game.id)):
            base_slug = game.slug or _slugify(game.title)
            slug = base_slug
            suffix = 2
            while slug in used_slugs:
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            used_slugs.add(slug)
            game.cover_url = game.cover_url or _legacy_cover_url(game.cover)
            if game.cover_url and not game.cover_url.startswith(("/files/", "/legacy-covers/")):
                game.cover_url = _legacy_cover_path(game.cover_url) or game.cover_url
            game.slug = slug

        session.flush()
        if not session.get(AppMigration, "legacy-metadata-v2"):
            for game in session.scalars(select(Game)):
                if not game.categories:
                    values = list(dict.fromkeys(
                        value for value in (game.category1, game.category2, game.category3) if value
                    ))
                    game.categories = [
                        GameCategory(game_id=game.id, name=value, position=position)
                        for position, value in enumerate(values)
                    ]
                if not game.store_links:
                    values = [
                        getattr(game, field)
                        for field in ("store1", "store2", "store3", "store4", "store5")
                    ]
                    game.store_links = [
                        GameStoreLink(
                            game_id=game.id,
                            url=value,
                            label=_store_label(value),
                            position=position,
                        )
                        for position, value in enumerate(
                            value for value in values if value and _is_http_url(value)
                        )
                    ]
            session.add(AppMigration(name="legacy-metadata-v2"))

        if not session.get(AppMigration, "legacy-platform-files-v1"):
            for game in session.scalars(select(Game)):
                for attribute, platform in LEGACY_PLATFORMS.items():
                    value = getattr(game, attribute)
                    if not value:
                        continue
                    value = str(value).strip()
                    if not value:
                        continue
                    if "://" in value:
                        if not _is_http_url(value):
                            continue
                        session.add(
                            GameFile(
                                game_id=game.id,
                                platform=platform,
                                original_name=value,
                                url=value,
                            )
                        )
                    else:
                        filename = Path(value.replace("\\", "/")).name
                        session.add(
                            GameFile(
                                game_id=game.id,
                                platform=platform,
                                original_name=filename,
                                stored_name=f"legacy/{platform}/{filename}",
                            )
                        )
            session.add(AppMigration(name="legacy-platform-files-v1"))
        session.commit()

    with engine.begin() as connection:
            for index in Game.__table__.indexes:
                index.create(connection, checkfirst=True)


def _store_label(value):
    from urllib.parse import urlparse

    host = urlparse(value).hostname or value
    return host.removeprefix("www.")


def file_href(slug, file_id):
    return f"/{slug}/files/{file_id}"


def get_game_files(session, game_id, slug=None):
    slug = slug or session.scalar(select(Game.slug).where(Game.id == game_id))
    files = session.scalars(
        select(GameFile).where(GameFile.game_id == game_id).order_by(GameFile.id)
    )
    return [
        {
            "id": item.id,
            "platform": item.platform,
            "platform_label": PLATFORMS[item.platform],
            "name": item.original_name,
            "href": _is_http_url(item.url) and item.url or file_href(slug, item.id),
            "url": _is_http_url(item.url) and item.url or None,
            "stored_name": item.stored_name,
        }
        for item in files
    ]


def _platforms(browser_url, files):
    present = {item["platform"] for item in files}
    if _public_url(browser_url, allow_local=True):
        present.add("browser")
    return [key for key in PLATFORMS if key != "cover" and key in present]


def all_category_names(session):
    return list(session.scalars(select(GameCategory.name).distinct().order_by(GameCategory.name)))


def get_game(session, game_id):
    game = session.get(Game, game_id)
    if not game:
        return None
    files = get_game_files(session, game_id, game.slug)
    cover = _public_cover_url(game.cover_url or "") or _public_cover_url(_legacy_cover_url(game.cover))
    raw_cover = re.fullmatch(r"/files/(\d+)", cover)
    if raw_cover:
        cover = file_href(game.slug, raw_cover.group(1))
    else:
        cover = _legacy_cover_path(cover) or cover
    return {
        "id": game.id,
        "title": game.title,
        "description": game.description or "",
        "note": game.note or "",
        "cover": cover,
        "ttb": game.time or "",
        "players": game.players or "",
        "category": [item.name for item in game.categories],
        "developer": game.developer or "",
        "developer_link": _public_url(game.developer_link, allow_local=True),
        "links": [
            {"url": item.url, **store_info(item.url)}
            for item in game.store_links
            if _is_http_url(item.url)
        ],
        "browser_url": _public_url(game.browser_url, allow_local=True),
        "steam_app_id": game.steam_app_id or "",
        "slug": game.slug,
        "files": files,
        "platforms": _platforms(game.browser_url, files),
    }


def list_games(session):
    ordering = case(
        (Game.title.like("The %"), func.substr(Game.title, 5)),
        else_=Game.title,
    ).collate("NOCASE")
    return [
        {
            **get_game(session, game.id),
        }
        for game in session.scalars(select(Game).order_by(ordering))
    ]


def unique_slug(session, title, exclude_id=None):
    base = _slugify(title)
    candidate = base
    suffix = 2
    while True:
        query = select(Game.id).where(Game.slug == candidate)
        if exclude_id is not None:
            query = query.where(Game.id != exclude_id)
        if candidate not in RESERVED_SLUGS and session.scalar(query) is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1
