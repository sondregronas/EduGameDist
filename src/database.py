import base64
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from sqlalchemy import (
    Boolean,
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
RESERVED_SLUGS = {
    "api", "assets", "files", "legacy-covers", "health", "install", "vilkar",
    "settings", "login", "logout", "logo",
}
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
    hidden: Mapped[bool] = mapped_column("Hidden", Boolean, default=False, server_default="0")
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


class Category(Base):
    """A category in the shared list that games pick from. Renaming it renames it on every game."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(collation="NOCASE"), unique=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class GameCategory(Base):
    """Links a game to a category, in the order the game shows its categories."""

    __tablename__ = "game_category_links"
    __table_args__ = (
        UniqueConstraint("game_id", "category_id", name="uq_game_category"),
        Index("idx_game_category_links_order", "game_id", "position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    game: Mapped[Game] = relationship(back_populates="categories", init=False, repr=False)
    category: Mapped[Category] = relationship(init=False, repr=False, lazy="joined")

    @property
    def name(self):
        return self.category.name


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


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


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
        for column, definition in (
            ("CoverUrl", "TEXT"),
            ("SteamAppId", "TEXT"),
            ("Slug", "TEXT"),
            ("Hidden", "BOOLEAN NOT NULL DEFAULT 0"),
        ):
            if column.lower() not in columns:
                connection.execute(text(f'ALTER TABLE games ADD COLUMN "{column}" {definition}'))
        if "position" not in {column["name"] for column in inspect(connection).get_columns("categories")}:
            connection.execute(text("ALTER TABLE categories ADD COLUMN position INTEGER NOT NULL DEFAULT 0"))

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
        if not session.get(AppMigration, "category-inventory-v1"):
            # Earlier versions stored category names per game; turn them into one shared list.
            if inspect(session.connection()).has_table("game_categories"):
                rows = session.execute(text(
                    "SELECT game_id, name FROM game_categories WHERE game_id IN (SELECT id FROM games) "
                    "ORDER BY game_id, position, id"
                )).all()
                for game_id, name in rows:
                    name = " ".join(str(name or "").split())
                    if name:
                        _link_category(session, game_id, category_named(session, name, create=True))
                session.execute(text("DROP TABLE game_categories"))
            session.add(AppMigration(name="category-inventory-v1"))

        if not session.get(AppMigration, "category-order-v1"):
            # Start the shared list in alphabetical order; admins can reorder it afterwards.
            for position, category in enumerate(sorted(session.scalars(select(Category)), key=lambda item: item.name.casefold())):
                category.position = position
            session.add(AppMigration(name="category-order-v1"))

        if not session.get(AppMigration, "legacy-metadata-v2"):
            for game in session.scalars(select(Game)):
                if not game.categories:
                    for value in (game.category1, game.category2, game.category3):
                        if value and value.strip():
                            _link_category(session, game.id, category_named(session, value.strip(), create=True))
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


def category_named(session, name, create=False):
    """Find a category by name regardless of case, optionally creating it."""
    wanted = name.casefold()
    for category in session.scalars(select(Category)):
        if category.name.casefold() == wanted:
            return category
    if not create:
        return None
    last = session.scalar(select(func.max(Category.position)))
    category = Category(name=name, position=0 if last is None else last + 1)
    session.add(category)
    session.flush()
    return category


def _link_category(session, game_id, category):
    links = session.scalars(select(GameCategory).where(GameCategory.game_id == game_id)).all()
    if all(link.category_id != category.id for link in links):
        session.add(GameCategory(game_id=game_id, category_id=category.id, position=len(links)))
        session.flush()


def all_categories(session, counts=False):
    """The shared category list in its chosen order, optionally with how many games use each one."""
    categories = session.scalars(select(Category).order_by(Category.position, Category.name)).all()
    totals = {}
    if counts:
        totals = dict(session.execute(
            select(GameCategory.category_id, func.count()).group_by(GameCategory.category_id)
        ).all())
    return [
        {"id": category.id, "name": category.name, **({"games": totals.get(category.id, 0)} if counts else {})}
        for category in categories
    ]


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
        "categories": [{"id": item.category_id, "name": item.name} for item in game.categories],
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
        "hidden": bool(game.hidden),
        "files": files,
        "platforms": _platforms(game.browser_url, files),
    }


def list_games(session, include_hidden=True):
    ordering = case(
        (Game.title.like("The %"), func.substr(Game.title, 5)),
        else_=Game.title,
    ).collate("NOCASE")
    query = select(Game).order_by(ordering)
    if not include_hidden:
        query = query.where(Game.hidden.is_(False))
    return [get_game(session, game.id) for game in session.scalars(query)]


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
