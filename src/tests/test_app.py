import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import patch

from sqlalchemy import delete, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as app_module
import database
import stores
from app import create_admin_app, create_public_app
from stores import FetchError
from database import (
    AppMigration,
    Game,
    GameCategory,
    GameFile,
    GameStoreLink,
    initialize_db,
    make_engine,
)


def fake_fetch(routes):
    def fetch(url, **_kwargs):
        for prefix, result in routes.items():
            if url.startswith(prefix):
                return result
        raise FetchError(f"unexpected request: {url}")

    return fetch


class EduGameDistAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        data_dir = Path(self.temp_dir.name) / "missing" / "data"
        self.admin = create_admin_app(data_dir)
        self.public = create_public_app(data_dir)
        self.engines = [
            self.admin.extensions["database_engine"],
            self.public.extensions["database_engine"],
        ]
        self.admin.config["TESTING"] = True
        self.public.config["TESTING"] = True
        self.admin_client = self.admin.test_client()
        self.public_client = self.public.test_client()

    def tearDown(self):
        for engine in self.engines:
            engine.dispose()
        self.temp_dir.cleanup()

    def create_game(self, **overrides):
        values = {
            "title": "Test Game",
            "description": "A test description",
            "categories": ["Puzzle", "Adventure"],
            "store_links": ["https://store.steampowered.com/app/10/"],
            "browser_url": "https://example.com/play",
        }
        values.update(overrides)
        response = self.admin_client.post("/api/games", json=values)
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        return response.json["id"], response.json["slug"]

    def upload(self, game_id, content, name, platform="windows"):
        return self.admin_client.post(
            f"/api/games/{game_id}/files",
            data=content,
            content_type="application/octet-stream",
            headers={"X-Platform": platform, "X-File-Name": name},
        )
    def test_admin_edits_normalized_metadata_and_public_is_read_only(self):
        game_id, slug = self.create_game()
        response = self.admin_client.put(
            f"/api/games/{game_id}",
            json={
                "title": "Updated Game",
                "description": "Updated description",
                "categories": ["Puzzle", "Co-op", "Classroom"],
                "store_links": [
                    "https://store.steampowered.com/app/10/",
                    "https://itch.io/game",
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        game = self.admin_client.get("/api/games").json[0]
        self.assertEqual(game["categories"], ["Puzzle", "Co-op", "Classroom"])
        self.assertEqual(len(game["links"]), 2)
        with Session(self.admin.extensions["database_engine"]) as session:
            self.assertEqual(
                session.scalar(select(func.count()).select_from(GameCategory).where(
                    GameCategory.game_id == game_id
                )),
                3,
            )
            self.assertEqual(
                session.scalar(select(func.count()).select_from(GameStoreLink).where(
                    GameStoreLink.game_id == game_id
                )),
                2,
            )
        public_page = self.public_client.get(f"/{response.json['slug']}")
        self.assertEqual(public_page.status_code, 200)
        self.assertIn("Updated description".encode(), public_page.data)
        self.assertNotEqual(slug, response.json["slug"])
        self.assertEqual(self.public_client.post("/api/games").status_code, 404)

    def test_multiple_files_are_streamed_in_one_request_and_served_unchanged(self):
        game_id, slug = self.create_game()
        first = self.upload(game_id, b"12345678abcdef" * 1000, "Windows-build.zip")
        second = self.upload(game_id, b"second build", "Windows-patch.zip")
        self.assertEqual(first.status_code, 201, first.get_data(as_text=True))
        self.assertEqual(second.status_code, 201, second.get_data(as_text=True))
        self.assertEqual(first.json["size"], 14000)

        response = self.public_client.get(first.json["href"])
        self.assertEqual(response.data, b"12345678abcdef" * 1000)
        response.close()
        page = self.public_client.get(f"/{slug}")
        self.assertIn(b"Windows-build.zip", page.data)
        self.assertIn(b"Windows-patch.zip", page.data)
        self.assertIn("14,0 KB".encode(), page.data)
        records = self.admin_client.get("/api/games").json[0]["files"]
        self.assertEqual(len(records), 2)
        self.assertNotIn("stored_name", records[0])
        self.assertEqual(list(Path(self.admin.config["TEMP_DIR"]).iterdir()), [])

    def test_upload_rejects_empty_bad_platform_and_truncated_files(self):
        game_id, _slug = self.create_game()
        self.assertIn(self.upload(game_id, b"", "empty.zip").status_code, (400, 411))
        self.assertEqual(self.upload(game_id, b"x", "x.zip", platform="amiga").status_code, 400)
        self.assertEqual(self.upload(game_id, b"x", "x.exe", platform="cover").status_code, 400)
        self.assertEqual(self.upload(999, b"x", "x.zip").status_code, 404)
    def test_uploaded_cover_is_shown_inline_and_file_can_be_removed(self):
        game_id, slug = self.create_game()
        response = self.upload(game_id, b"fake image data", "cover.png", platform="cover")
        self.assertEqual(response.status_code, 201)
        image = self.public_client.get(response.json["href"])
        self.assertEqual(image.headers["Content-Disposition"].split(";")[0], "inline")
        image.close()
        page = self.public_client.get(f"/{slug}")
        self.assertIn(response.json["href"].encode(), page.data)
        removed = self.admin_client.delete(f"/api/files/{response.json['id']}")
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(self.public_client.get(response.json["href"]).status_code, 404)

    def test_admin_app_has_no_login_and_rejects_cross_origin_mutations(self):
        self.assertEqual(self.admin_client.get("/").status_code, 200)
        rejected = self.admin_client.post(
            "/api/games",
            json={"title": "Cross-site"},
            headers={"Origin": "https://attacker.invalid"},
        )
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(self.admin_client.post("/api/games", json={"title": "No auth"}).status_code, 201)

    def test_public_database_connection_is_read_only(self):
        with Session(self.public.extensions["database_engine"]) as session:
            with self.assertRaises(OperationalError):
                session.execute(delete(Game))

    def test_steam_lookup_uses_validated_app_id_and_populates_fields(self):
        payload = {
            "123": {
                "success": True,
                "data": {
                    "name": "Steam Game",
                    "short_description": "<b>A short description.</b>",
                    "header_image": "https://cdn.akamai.steamstatic.com/header.jpg?t=17",
                    "developers": ["Studio"],
                    "website": "https://studio.example/",
                },
            }
        }
        fetch = fake_fetch({"https://store.steampowered.com/api/appdetails?appids=123": (json.dumps(payload).encode(), "application/json")})
        with patch("app._fetch", side_effect=fetch):
            result = self.admin_client.post("/api/steam", json={"steam": "https://store.steampowered.com/app/123/game/"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["title"], "Steam Game")
        self.assertEqual(result.json["description"], "A short description.")
        self.assertEqual(result.json["steam_app_id"], "123")
        self.assertEqual(result.json["developer_link"], "https://studio.example/")
        self.assertEqual(result.json["cover_url"], "https://cdn.akamai.steamstatic.com/header.jpg")
        self.assertEqual(result.json["store_links"][0]["key"], "steam")
        invalid = self.admin_client.post("/api/steam", json={"steam": "https://evil.example/app/123"})
        self.assertEqual(invalid.status_code, 400)

    def test_steam_lookup_by_title_needs_an_exact_match(self):
        search = {"items": [{"type": "app", "name": "Celeste", "id": 504230}, {"type": "app", "name": "Celeste 2", "id": 1}]}
        details = {"504230": {"success": True, "data": {"name": "Celeste", "short_description": "Climb."}}}
        fetch = fake_fetch({
            "https://store.steampowered.com/api/storesearch/": (json.dumps(search).encode(), "application/json"),
            "https://store.steampowered.com/api/appdetails?appids=504230": (json.dumps(details).encode(), "application/json"),
        })
        with patch("app._fetch", side_effect=fetch):
            found = self.admin_client.post("/api/steam", json={"steam": "celeste"})
            missing = self.admin_client.post("/api/steam", json={"steam": "Cel"})
        self.assertEqual(found.json["steam_app_id"], "504230")
        self.assertEqual(found.json["developer_link"], "")
        self.assertEqual(missing.status_code, 404)

    def test_remote_cover_is_downloaded_and_replaced_on_change(self):
        image = b"\x89PNG fake image"
        fetch = fake_fetch({"https://cdn.example/": (image, "image/png")})
        with patch("app._fetch", side_effect=fetch):
            game_id, slug = self.create_game(cover_url="https://cdn.example/header.jpg")
            first = self.admin_client.get(f"/api/games/{game_id}").json["cover_url"]
            self.assertRegex(first, r"^/[\w-]+/files/\d+$")
            old = self.public_client.get("/files/" + first.rsplit("/", 1)[1])
            self.assertEqual((old.status_code, old.headers["Location"]), (301, first))
            download = self.public_client.get(first)
            self.assertEqual(download.data, image)
            download.close()
            response = self.admin_client.put(f"/api/games/{game_id}", json={"cover_url": "https://cdn.example/other.png"})
            self.assertIsNone(response.json["warning"])
        second = self.admin_client.get(f"/api/games/{game_id}").json["cover_url"]
        self.assertNotEqual(first, second)
        self.assertEqual(self.public_client.get(first).status_code, 404)
        self.assertEqual(len(list(Path(self.admin.config["UPLOAD_DIR"]).iterdir())), 1)
        self.assertIn(second.encode(), self.public_client.get(f"/{slug}").data)

    def test_failed_cover_download_keeps_link_and_warns(self):
        with patch("app._fetch", side_effect=FetchError("nede")):
            response = self.admin_client.post("/api/games", json={"title": "Offline", "cover_url": "https://cdn.example/x.jpg"})
        self.assertEqual(response.status_code, 201)
        self.assertIn("Lenken beholdes", response.json["warning"])
        self.assertEqual(self.admin_client.get(f"/api/games/{response.json['id']}").json["cover_url"], "https://cdn.example/x.jpg")

    def test_failed_cover_download_reports_reason(self):
        with patch("app._fetch", side_effect=FetchError("nede")):
            response = self.admin_client.post("/api/games", json={"title": "Offline", "cover_url": "https://cdn.example/x.jpg"})
        self.assertIn("nede", response.json["warning"])
        with patch("app._fetch", side_effect=FetchError("nede")):
            result = self.admin_client.post("/api/covers/localize")
        self.assertEqual(result.json["failed"], 1)
        self.assertIn("nede", result.json["reason"])

    def test_cover_with_generic_content_type_is_sniffed(self):
        fetch = fake_fetch({"https://cdn.example/": (b"\xff\xd8\xff\xe0 jpeg", "application/octet-stream")})
        with patch("app._fetch", side_effect=fetch):
            response = self.admin_client.post("/api/games", json={"title": "Sniff", "cover_url": "https://cdn.example/x"})
        self.assertIsNone(response.json["warning"])

    def test_steam_cdn_may_resolve_to_a_local_cache(self):
        private = [(2, 1, 6, "", ("10.0.0.5", 443))]
        with patch("app.socket.getaddrinfo", return_value=private):
            app_module._require_public_host("shared.akamai.steamstatic.com", 443)
            with self.assertRaises(FetchError):
                app_module._require_public_host("evil.example", 443)

    def test_non_image_cover_is_rejected(self):
        fetch = fake_fetch({"https://cdn.example/": (b"<svg/>", "image/svg+xml")})
        with patch("app._fetch", side_effect=fetch):
            response = self.admin_client.post("/api/games", json={"title": "Svg", "cover_url": "https://cdn.example/x.svg"})
        self.assertIsNotNone(response.json["warning"])
        self.assertEqual(list(Path(self.admin.config["UPLOAD_DIR"]).iterdir()), [])

    def test_partial_update_leaves_other_fields_alone(self):
        game_id, _slug = self.create_game()
        self.upload(game_id, b"image", "cover.png", platform="cover")
        self.upload(game_id, b"zip", "game.zip")
        cover = self.admin_client.get(f"/api/games/{game_id}").json["cover_url"]
        self.assertEqual(self.admin_client.put(f"/api/games/{game_id}", json={"players": "2-4"}).status_code, 200)
        game = self.admin_client.get(f"/api/games/{game_id}").json
        self.assertEqual(game["players"], "2-4")
        self.assertEqual(game["cover_url"], cover)
        self.assertEqual(game["title"], "Test Game")
        self.assertEqual(game["categories"], ["Puzzle", "Adventure"])
        self.assertEqual(len(game["files"]), 2)

    def test_replacing_cover_upload_removes_the_old_cover_file(self):
        game_id, _slug = self.create_game()
        self.upload(game_id, b"first", "one.png", platform="cover")
        self.upload(game_id, b"second", "two.png", platform="cover")
        self.assertEqual(len(list(Path(self.admin.config["UPLOAD_DIR"]).iterdir())), 1)

    def test_store_discovery_endpoint_returns_exact_matches(self):
        gog = {"products": [{"title": "Celeste", "storeLink": "https://www.gog.com/en/game/celeste"}]}
        itch = (
            '<div class="game_cell_data"><div class="game_title"><a href="https://maddy.itch.io/celeste64" '
            'class="title game_link" data-x="1">Celeste 64</a></div></div>'
        )
        humble = '<meta property="og:title" content="Buy Celeste from the Humble Store">'
        fetch = fake_fetch({
            "https://catalog.gog.com/": (json.dumps(gog).encode(), "application/json"),
            "https://itch.io/search": (itch.encode(), "text/html"),
            "https://www.humblebundle.com/store/celeste": (humble.encode(), "text/html"),
        })
        with patch("app._fetch", side_effect=fetch):
            result = self.admin_client.post("/api/stores", json={"title": "Celeste"})
        links = {item["key"]: item["url"] for item in result.json["links"]}
        self.assertEqual(links, {
            "gog": "https://www.gog.com/en/game/celeste",
            "humble": "https://www.humblebundle.com/store/celeste",
        })

    def test_itch_requires_unique_or_developer_matched_result(self):
        def page(*entries):
            return "".join(
                f'<div class="game_cell_data"><div class="game_title"><a href="{url}" class="title game_link" x="1">Dup</a></div>'
                f'<div class="game_author"><a href="/">{author}</a></div></div>'
                for url, author in entries
            ).encode(), "text/html"

        both = page(("https://a.itch.io/dup", "Alpha"), ("https://b.itch.io/dup", "Beta Games"))
        self.assertIsNone(stores._find_itch("Dup", "", lambda *a, **k: both))
        self.assertEqual(stores._find_itch("Dup", "Beta", lambda *a, **k: both), "https://b.itch.io/dup")

    def test_store_info_matches_hosts_not_substrings(self):
        self.assertEqual(stores.store_info("https://someone.itch.io/game")["key"], "itch")
        self.assertEqual(stores.store_info("https://evil.example/steampowered.com")["key"], "link")
        self.assertEqual(stores.store_info("https://notgog.com/x")["key"], "link")

    def test_fetch_refuses_private_addresses(self):
        for host in ("127.0.0.1", "10.0.0.5", "169.254.169.254", "localhost"):
            with self.assertRaises(FetchError):
                app_module._require_public_host(host, 80)
        with self.assertRaises(FetchError):
            app_module._fetch("file:///etc/passwd")

    def test_admin_pages_have_inline_editing_and_public_pages_do_not(self):
        game_id, slug = self.create_game()
        admin_page = self.admin_client.get(f"/{slug}").get_data(as_text=True)
        public_page = self.public_client.get(f"/{slug}").get_data(as_text=True)
        for marker in ("edit-toggle", "tag-add-btn", "dropzone", 'data-field="title"'):
            self.assertIn(marker, admin_page)
            self.assertNotIn(marker, public_page)
        self.assertIn("add-game", self.admin_client.get("/").get_data(as_text=True))
        self.assertNotIn("add-game", self.public_client.get("/").get_data(as_text=True))
        self.assertNotIn("/install", public_page.split('class="downloads"')[0].split("<main")[1])

    def test_game_page_links_to_platform_help_and_shows_store_icons(self):
        game_id, slug = self.create_game(store_links=["https://store.steampowered.com/app/10/", "https://x.itch.io/g"])
        self.upload(game_id, b"zip", "game.zip", platform="mac")
        page = self.public_client.get(f"/{slug}").get_data(as_text=True)
        self.assertIn('href="/install#mac"', page)
        self.assertIn("icons.svg#steam", page)
        self.assertIn("icons.svg#itch", page)

    def test_titles_cannot_take_reserved_routes(self):
        _game_id, slug = self.create_game(title="Install")
        self.assertNotEqual(slug, "install")
        self.assertEqual(self.public_client.get("/install").status_code, 200)
        self.assertEqual(self.public_client.get(f"/{slug}").status_code, 200)

    def test_note_renders_safe_html(self):
        from richtext import rich_text

        rendered = str(rich_text(
            'Fra EWC.<br><a href="https://x.org/a.pdf" onclick="x()">Ressurshefte</a>'
            '<script>alert(1)</script><a href="javascript:alert(1)">bad</a><img src=x onerror=y>\nny linje'
        ))
        self.assertIn('<a href="https://x.org/a.pdf" target="_blank" rel="noopener noreferrer">Ressurshefte</a>', rendered)
        self.assertIn("EWC.<br><a", rendered)
        self.assertNotIn("onclick", rendered)
        self.assertNotIn("alert", rendered.replace("bad", ""))
        self.assertNotIn("javascript", rendered)
        self.assertNotIn("<img", rendered)
        self.assertIn("<br>ny linje", rendered)
        self.assertEqual(str(rich_text("a < b & c")), "a &lt; b &amp; c")
        game_id, slug = self.create_game(note='Hei<br><a href="https://x.org/">lenke</a>')
        page = self.public_client.get(f"/{slug}").data.decode()
        self.assertIn('<a href="https://x.org/" target="_blank"', page)

    def test_human_size_uses_norwegian_decimal_comma(self):
        self.assertEqual(app_module._human_size(999), "999 B")
        self.assertEqual(app_module._human_size(1_500_000), "1,5 MB")
        self.assertEqual(app_module._human_size(21_474_836_480), "21,5 GB")
    def test_existing_schema_migrates_categories_links_downloads_and_cover(self):
        engine = make_engine(Path(self.temp_dir.name) / "legacy" / "gamedb.db")
        self.engines.append(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql(
                """
                CREATE TABLE games (
                    id INTEGER PRIMARY KEY, Title TEXT NOT NULL, Description TEXT, Note TEXT,
                    Cover BLOB, Time TEXT, Players TEXT, Category1 TEXT, Category2 TEXT,
                    Category3 TEXT, Developer TEXT, Developer_link TEXT, Url TEXT,
                    Win_dl TEXT, Mac_dl TEXT, Linux_dl TEXT, Android_dl TEXT,
                    Store1 TEXT, Store2 TEXT, Store3 TEXT, Store4 TEXT, Store5 TEXT
                )
                """
            )
            connection.exec_driver_sql(
                """
                INSERT INTO games
                    (Title, Description, Cover, Category1, Category2, Store1, Win_dl)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "Legacy Game",
                    "Old description",
                    json.dumps([{"url": "https://old.example/download/project/table/field/Cover/legacy.jpg"}]),
                    "Puzzle",
                    "Puzzle",
                    "https://store.steampowered.com/app/10/",
                    "old-build.zip",
                ),
            )
        initialize_db(engine)
        with Session(engine) as session:
            game = session.scalar(select(Game).where(Game.title == "Legacy Game"))
            self.assertEqual([item.name for item in game.categories], ["Puzzle"])
            self.assertEqual([item.url for item in game.store_links], ["https://store.steampowered.com/app/10/"])
            downloads = session.scalars(select(GameFile).where(GameFile.game_id == game.id)).all()
            self.assertEqual(len(downloads), 1)
            self.assertEqual(downloads[0].stored_name, "legacy/windows/old-build.zip")
            self.assertEqual(game.cover_url, "/legacy-covers/legacy.jpg")
            self.assertEqual(database._legacy_cover_url("/download/noco/Games/Games/Cover/w0CeOl.jpg"), "/legacy-covers/w0CeOl.jpg")
            self.assertEqual(database._legacy_cover_url("https://cdn.example/Cover/x.jpg"), "https://cdn.example/Cover/x.jpg")
            self.assertEqual(
                database._legacy_cover_url(json.dumps([{"path": "download/noco/Games/Games/Cover/a%20b.jpg"}])),
                "/legacy-covers/a b.jpg",
            )
            self.assertIsNotNone(session.get(AppMigration, "legacy-metadata-v2"))


class AdminLoginTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        patcher = mock.patch.dict(os.environ, {"ADMIN_PASSWORD": "hemmelig", "SECRET_KEY": ""})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.app = create_admin_app(Path(self.temp_dir.name) / "data")
        self.addCleanup(self.app.extensions["database_engine"].dispose)
        self.client = self.app.test_client()

    def test_everything_requires_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/login"))
        self.assertEqual(self.client.get("/api/games").status_code, 401)
        self.assertEqual(self.client.get("/health").status_code, 200)
        with self.client.get("/assets/css/app.css") as asset:
            self.assertEqual(asset.status_code, 200)

    def test_wrong_password_is_rejected_and_throttled(self):
        for _ in range(5):
            self.assertEqual(self.client.post("/login", data={"password": "feil"}).status_code, 401)
        self.assertEqual(self.client.post("/login", data={"password": "hemmelig"}).status_code, 429)

    def test_login_logout_and_safe_redirect(self):
        response = self.client.post("/login", data={"password": "hemmelig", "next": "//evil.example"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        self.assertEqual(self.client.get("/api/games").status_code, 200)
        self.assertIn("Logg ut", self.client.get("/").get_data(as_text=True))
        self.client.post("/logout")
        self.assertEqual(self.client.get("/api/games").status_code, 401)

    def test_disabled_without_password(self):
        with mock.patch.dict(os.environ, {"ADMIN_PASSWORD": ""}):
            app = create_admin_app(Path(self.temp_dir.name) / "open")
        self.addCleanup(app.extensions["database_engine"].dispose)
        self.assertEqual(app.test_client().get("/api/games").status_code, 200)


if __name__ == "__main__":
    unittest.main()
