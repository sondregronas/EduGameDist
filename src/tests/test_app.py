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
    Category,
    Game,
    GameCategory,
    GameFile,
    GameStoreLink,
    Setting,
    initialize_db,
    make_engine,
)

PNG = b"\x89PNG\r\n\x1a\n fake png"


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
        self.data_dir = Path(self.temp_dir.name) / "missing" / "data"
        self.games_dir = Path(self.temp_dir.name) / "games"
        self.admin = create_admin_app(self.data_dir, self.games_dir)
        self.public = create_public_app(self.data_dir, self.games_dir)
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
        values["categories"] = self.category_ids(values["categories"])
        response = self.admin_client.post("/api/games", json=values)
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        return response.json["id"], response.json["slug"]

    def category_ids(self, names):
        """Categories come from the shared list; adding an existing name returns that category."""
        return [self.admin_client.post("/api/categories", json={"name": name}).json["id"] for name in names]

    def category_names(self, game_id):
        return [category["name"] for category in self.admin_client.get(f"/api/games/{game_id}").json["categories"]]

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
                "categories": self.category_ids(["Puzzle", "Co-op", "Classroom"]),
                "store_links": [
                    "https://store.steampowered.com/app/10/",
                    "https://itch.io/game",
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        game = self.admin_client.get("/api/games").json[0]
        self.assertEqual([category["name"] for category in game["categories"]], ["Puzzle", "Co-op", "Classroom"])
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
        self.assertEqual(self.category_names(game_id), ["Puzzle", "Adventure"])
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

    def test_game_files_are_stored_in_per_game_folders_under_their_own_name(self):
        game_id, slug = self.create_game()
        first = self.upload(game_id, b"one", "Setup.zip")
        second = self.upload(game_id, b"two", "Setup.zip")
        odd = self.upload(game_id, b"three", 'bad:name?.zip', platform="mac")
        folder = self.games_dir / "Windows" / slug
        self.assertEqual((folder / "Setup.zip").read_bytes(), b"one")
        self.assertEqual((folder / "Setup (2).zip").read_bytes(), b"two")
        self.assertEqual((self.games_dir / "Mac" / slug / "bad_name_.zip").read_bytes(), b"three")
        download = self.public_client.get(odd.json["href"])
        self.assertEqual(download.data, b"three")
        self.assertIn("bad:name?.zip", download.headers["Content-Disposition"])
        download.close()
        with self.public_client.get(second.json["href"]) as response:
            self.assertEqual(response.data, b"two")
        self.assertEqual(first.json["name"], "Setup.zip")
        self.assertEqual(list(Path(self.admin.config["UPLOAD_DIR"]).iterdir()), [])
        self.assertEqual(list((self.games_dir / "Windows" / ".upload-tmp").iterdir()), [])

    def test_safe_filename_handles_unsafe_and_long_names(self):
        self.assertEqual(app_module._safe_filename("../../etc/passwd"), "_.._etc_passwd")
        self.assertEqual(app_module._safe_filename(" ..hidden.zip. "), "hidden.zip")
        self.assertEqual(app_module._safe_filename("CON.zip"), "_CON.zip")
        self.assertEqual(app_module._safe_filename("..."), "fil")
        long_name = app_module._safe_filename("æ" * 300 + ".zip")
        self.assertTrue(long_name.endswith(".zip"))
        self.assertLessEqual(len(long_name.encode("utf-8")), 200)

    def test_renaming_a_game_moves_its_files_to_the_new_folder(self):
        game_id, slug = self.create_game()
        upload = self.upload(game_id, b"zip", "game.zip")
        self.upload(game_id, b"apk", "game.apk", platform="android")
        response = self.admin_client.put(f"/api/games/{game_id}", json={"title": "Renamed Game"})
        new_slug = response.json["slug"]
        self.assertNotEqual(slug, new_slug)
        self.assertTrue((self.games_dir / "Windows" / new_slug / "game.zip").is_file())
        self.assertTrue((self.games_dir / "Android" / new_slug / "game.apk").is_file())
        self.assertFalse((self.games_dir / "Windows" / slug).exists())
        self.assertFalse((self.games_dir / "Android" / slug).exists())
        with self.public_client.get(f"/{new_slug}/files/{upload.json['id']}") as download:
            self.assertEqual(download.data, b"zip")

    def test_deleting_files_and_games_removes_their_folders(self):
        game_id, slug = self.create_game()
        upload = self.upload(game_id, b"zip", "game.zip")
        self.upload(game_id, b"dmg", "game.dmg", platform="mac")
        self.assertEqual(self.admin_client.delete(f"/api/files/{upload.json['id']}").status_code, 200)
        self.assertFalse((self.games_dir / "Windows" / slug).exists())
        self.assertTrue((self.games_dir / "Mac" / slug / "game.dmg").is_file())
        self.assertEqual(self.admin_client.delete(f"/api/games/{game_id}").status_code, 200)
        self.assertFalse((self.games_dir / "Mac" / slug).exists())

    def test_existing_uploads_are_moved_into_game_folders_on_startup(self):
        game_id, slug = self.create_game()
        other_id, other_slug = self.create_game(title="Other Game")
        cover = self.upload(game_id, PNG, "cover.png", platform="cover")
        upload_dir = Path(self.admin.config["UPLOAD_DIR"])
        (upload_dir / "0123abcd.zip").write_bytes(b"old upload")
        loose = self.games_dir / "Windows" / "manual.zip"
        loose.parent.mkdir(parents=True, exist_ok=True)
        loose.write_bytes(b"manual")
        with Session(self.admin.extensions["database_engine"]) as session:
            session.add_all([
                GameFile(game_id=game_id, platform="linux", original_name="Linux build.zip", stored_name="0123abcd.zip"),
                GameFile(game_id=game_id, platform="windows", original_name="manual.zip", stored_name="legacy/windows/manual.zip"),
                GameFile(game_id=other_id, platform="windows", original_name="manual.zip", stored_name="legacy/windows/manual.zip"),
                GameFile(game_id=other_id, platform="mac", original_name="gone.zip", stored_name="legacy/mac/gone.zip"),
            ])
            session.commit()
        for engine in self.engines:
            engine.dispose()

        restarted = create_admin_app(self.data_dir, self.games_dir)
        self.engines.append(restarted.extensions["database_engine"])
        self.assertEqual((self.games_dir / "Linux" / slug / "Linux build.zip").read_bytes(), b"old upload")
        self.assertEqual((self.games_dir / "Windows" / slug / "manual.zip").read_bytes(), b"manual")
        self.assertEqual((self.games_dir / "Windows" / other_slug / "manual.zip").read_bytes(), b"manual")
        self.assertFalse(loose.exists())
        self.assertFalse((upload_dir / "0123abcd.zip").exists())
        with Session(restarted.extensions["database_engine"]) as session:
            names = {item.original_name + ":" + str(item.game_id): item.stored_name for item in session.scalars(select(GameFile))}
        self.assertEqual(names[f"Linux build.zip:{game_id}"], f"games/Linux/{slug}/Linux build.zip")
        self.assertEqual(names[f"manual.zip:{other_id}"], f"games/Windows/{other_slug}/manual.zip")
        self.assertEqual(names[f"gone.zip:{other_id}"], "legacy/mac/gone.zip")
        self.assertNotIn("/", names[f"cover.png:{game_id}"])
        with restarted.test_client().get(f"/{slug}/files/{cover.json['id']}") as response:
            self.assertEqual(response.data, PNG)

    def test_uploads_stay_in_the_data_volume_when_the_games_folder_is_not_mounted(self):
        self.admin.config["GAMES_MOUNT_REQUIRED"] = True
        game_id, slug = self.create_game()
        upload = self.upload(game_id, b"zip", "game.zip")
        self.assertEqual(upload.status_code, 201)
        self.assertFalse((self.games_dir / "Windows").exists())
        self.assertEqual(len(list(Path(self.admin.config["UPLOAD_DIR"]).iterdir())), 1)
        with self.public_client.get(upload.json["href"]) as download:
            self.assertEqual(download.data, b"zip")
        self.assertIn("notice-warn", self.admin_client.get("/").get_data(as_text=True))

        mounted = lambda path: Path(path) == self.games_dir
        with patch("app.os.path.ismount", side_effect=mounted):
            self.assertEqual(self.upload(game_id, b"zip", "mounted.zip").status_code, 201)
            self.assertNotIn("notice-warn", self.admin_client.get("/").get_data(as_text=True))
        self.assertTrue((self.games_dir / "Windows" / slug / "mounted.zip").is_file())

    def test_hidden_games_are_only_shown_in_admin(self):
        game_id, slug = self.create_game()
        upload = self.upload(game_id, b"zip", "game.zip")
        self.assertEqual(self.admin_client.put(f"/api/games/{game_id}", json={"hidden": "yes"}).status_code, 400)
        self.assertEqual(self.admin_client.put(f"/api/games/{game_id}", json={"hidden": True}).status_code, 200)
        self.assertTrue(self.admin_client.get(f"/api/games/{game_id}").json["hidden"])
        self.assertNotIn(b"Test Game", self.public_client.get("/").data)
        self.assertEqual(self.public_client.get(f"/{slug}").status_code, 404)
        self.assertEqual(self.public_client.get(upload.json["href"]).status_code, 404)
        admin_index = self.admin_client.get("/").get_data(as_text=True)
        self.assertIn("is-concealed", admin_index)
        self.assertIn("icons.svg#eye-off", admin_index)
        self.assertEqual(self.admin_client.get(f"/{slug}").status_code, 200)
        for path in ("/assets/games/Windows/Games go here.txt", "/assets/Games/Windows/Games go here.txt"):
            self.assertEqual(self.public_client.get(path).status_code, 404)
        self.admin_client.put(f"/api/games/{game_id}", json={"hidden": False})
        self.assertEqual(self.public_client.get(f"/{slug}").status_code, 200)

    def test_front_page_filters_by_category_and_platform_with_dropdowns(self):
        game_id, slug = self.create_game(categories=["Puzzle", "Co-op"])
        self.create_game(title="Second", categories=["puzzle"], browser_url="")
        self.upload(game_id, b"zip", "game.zip")
        page = self.public_client.get("/").get_data(as_text=True)
        option = r'<li class="menu-option" role="option" data-value="{}" aria-selected="false">'
        self.assertRegex(page, option.format("puzzle") + r'<span class="menu-dot" style="--h: \d+"></span><span class="menu-text">[Pp]uzzle</span><span class="menu-count">2</span>')
        self.assertRegex(page, option.format("co-op") + r'.*?<span class="menu-count">1</span>')
        self.assertRegex(page, option.format("windows") + r'<svg[^>]*><use href="/assets/img/icons.svg#windows"/></svg><span class="menu-text">Windows</span>')
        self.assertRegex(page, option.format("browser"))
        self.assertNotIn('data-value="mac"', page)
        self.assertIn('href="/?category=puzzle"', self.public_client.get(f"/{slug}").get_data(as_text=True))

    def test_site_settings_change_title_front_page_and_menu(self):
        response = self.admin_client.put("/api/settings", json={
            "site_title": "Skolens spill",
            "hero_title": "Velkommen!",
            "hero_text": 'Ønsker du et spill? <a href="https://forms.example/ny">Si fra</a><script>alert(1)</script>',
            "nav": [
                {"key": "games", "label": "", "hidden": False},
                {"key": "link", "label": "Ønsk deg et spill", "url": "https://forms.example/ny", "new_tab": True},
                {"key": "terms", "label": "Regler", "hidden": True},
                {"key": "install", "label": "Hjelp", "hidden": False},
            ],
        })
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        page = self.public_client.get("/").get_data(as_text=True)
        self.assertIn("<title>Skolens spill</title>", page)
        self.assertIn("<h1>Velkommen!</h1>", page)
        self.assertIn('<a href="https://forms.example/ny" target="_blank" rel="noopener noreferrer">Si fra</a>', page)
        self.assertNotIn("alert(1)", page)
        nav = page.split('class="site-nav"')[1].split("</nav>")[0]
        self.assertLess(nav.index('href="/"'), nav.index("forms.example"))
        self.assertLess(nav.index("forms.example"), nav.index('href="/install"'))
        self.assertIn("Hjelp", nav)
        self.assertNotIn("/vilkar", nav)
        self.assertIn("<title>Installasjon · Skolens spill</title>", self.public_client.get("/install").get_data(as_text=True))

        self.admin_client.put("/api/settings", json={"site_title": "", "hero_title": "", "hero_text": ""})
        page = self.public_client.get("/").get_data(as_text=True)
        self.assertIn("<h1>Spilldistribusjon</h1>", page)
        self.assertNotIn('class="hero-text"', page)
        self.assertIn("Spill", self.admin_client.get("/settings").get_data(as_text=True))

    def test_categories_are_a_shared_list_that_games_pick_from(self):
        first = self.admin_client.post("/api/categories", json={"name": "  Strategi  "})
        self.assertEqual((first.status_code, first.json["name"], first.json["existing"]), (201, "Strategi", False))
        again = self.admin_client.post("/api/categories", json={"name": "strategi"})
        self.assertEqual((again.status_code, again.json["id"], again.json["existing"]), (200, first.json["id"], True))
        for bad in ("", "a|b", "x" * 101):
            self.assertEqual(self.admin_client.post("/api/categories", json={"name": bad}).status_code, 400)

        game_id, slug = self.create_game(categories=["Strategi", "Puzzle"])
        other_id, _other = self.create_game(title="Other", categories=["Puzzle"])
        puzzle = self.category_ids(["Puzzle"])[0]
        listed = {category["name"]: category["games"] for category in self.admin_client.get("/api/categories").json}
        self.assertEqual(listed, {"Puzzle": 2, "Strategi": 1})

        # Games can only pick categories from the list, by id.
        for categories in (["Puzzle"], [999], [True], "Puzzle"):
            response = self.admin_client.put(f"/api/games/{game_id}", json={"categories": categories})
            self.assertEqual(response.status_code, 400, categories)

        # Renaming changes the name everywhere, because games point at the same category.
        renamed = self.admin_client.put(f"/api/categories/{puzzle}", json={"name": "Gåter"})
        self.assertEqual((renamed.status_code, renamed.json["name"]), (200, "Gåter"))
        self.assertEqual(self.category_names(game_id), ["Strategi", "Gåter"])
        self.assertEqual(self.category_names(other_id), ["Gåter"])
        public = self.public_client.get(f"/{slug}").get_data(as_text=True)
        self.assertIn('href="/?category=g%C3%A5ter"', public)
        self.assertNotIn("Puzzle", public)
        self.assertEqual(self.admin_client.put(f"/api/categories/{puzzle}", json={"name": "STRATEGI"}).status_code, 409)
        self.assertEqual(self.admin_client.put(f"/api/categories/{puzzle}", json={"name": "gåter"}).status_code, 200)

        # Deleting removes it from every game.
        self.assertEqual(self.admin_client.delete(f"/api/categories/{puzzle}").status_code, 200)
        self.assertEqual(self.category_names(game_id), ["Strategi"])
        self.assertEqual(self.category_names(other_id), [])
        self.assertEqual(self.admin_client.delete(f"/api/categories/{puzzle}").status_code, 404)
        settings_page = self.admin_client.get("/settings").get_data(as_text=True)
        editor = json.loads(settings_page.split('id="settings-data">')[1].split("</script>")[0])
        self.assertEqual(editor["categories"], [{"id": first.json["id"], "name": "Strategi", "games": 1}])

    def test_category_order_can_be_changed_for_the_list_and_for_each_game(self):
        game_id, slug = self.create_game(categories=["Strategi", "Puzzle", "Adventure"])
        strategi, puzzle, adventure = self.category_ids(["Strategi", "Puzzle", "Adventure"])
        listed = lambda: [category["name"] for category in self.admin_client.get("/api/categories").json]
        self.assertEqual(listed(), ["Strategi", "Puzzle", "Adventure"])  # new categories go last

        # The shared list: reorder, and ids left out keep their place after the ones given.
        self.assertEqual(self.admin_client.put("/api/categories/order", json={"ids": [adventure, 999, strategi]}).status_code, 200)
        self.assertEqual(listed(), ["Adventure", "Strategi", "Puzzle"])
        self.assertEqual(self.admin_client.put("/api/categories/order", json={"ids": "nope"}).status_code, 400)
        page = self.public_client.get("/").get_data(as_text=True)
        menu = page.split('id="category-menu"')[1].split("</ul>")[0]
        self.assertLess(menu.index('data-value="adventure"'), menu.index('data-value="strategi"'))
        self.assertLess(menu.index('data-value="strategi"'), menu.index('data-value="puzzle"'))
        created = self.admin_client.post("/api/categories", json={"name": "Ny"}).json["id"]
        self.assertEqual(listed()[-1], "Ny")

        # A game's own order is the order of the ids it is saved with.
        self.admin_client.put(f"/api/games/{game_id}", json={"categories": [adventure, created, puzzle]})
        self.assertEqual(self.category_names(game_id), ["Adventure", "Ny", "Puzzle"])
        card = self.public_client.get("/").get_data(as_text=True).split(f'href="/{slug}"')[1].split("</article>")[0]
        self.assertLess(card.index(">Adventure<"), card.index(">Ny<"))

    def test_categories_can_be_changed_outside_edit_mode_and_from_the_front_page(self):
        _game_id, slug = self.create_game(categories=["Puzzle"])
        admin_game = self.admin_client.get(f"/{slug}").get_data(as_text=True)
        editor = admin_game.split('<div class="tag-editor">')[1].split("</div>")[0]
        self.assertIn('id="category-picker"', editor)
        self.assertNotIn('href="/?category=puzzle"', admin_game)
        self.assertIn('href="/?category=puzzle"', self.public_client.get(f"/{slug}").get_data(as_text=True))
        admin_index = self.admin_client.get("/").get_data(as_text=True)
        for marker in ('id="edit-categories"', 'id="categories-dialog"', 'id="category-manager"'):
            self.assertIn(marker, admin_index)
            self.assertNotIn(marker, self.public_client.get("/").get_data(as_text=True))
        inventory = json.loads(admin_index.split('id="category-data">')[1].split("</script>")[0])
        self.assertEqual(inventory, [{"id": self.category_ids(["Puzzle"])[0], "name": "Puzzle", "games": 1}])

    def test_per_game_category_names_are_migrated_to_the_shared_list(self):
        engine = self.admin.extensions["database_engine"]
        game_id, _slug = self.create_game(categories=[])
        other_id, _other = self.create_game(title="Other", categories=[])
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE game_categories (id INTEGER PRIMARY KEY, game_id INTEGER, name TEXT, position INTEGER)"
            )
            connection.exec_driver_sql(
                "INSERT INTO game_categories (game_id, name, position) VALUES (?, 'Puzzle', 0), (?, 'Co-op', 1), (?, 'puzzle', 0)",
                (game_id, game_id, other_id),
            )
            connection.exec_driver_sql(
                "DELETE FROM app_migrations WHERE name IN ('category-inventory-v1', 'category-order-v1')"
            )
        initialize_db(engine)
        self.assertEqual(self.category_names(game_id), ["Puzzle", "Co-op"])
        self.assertEqual(self.category_names(other_id), ["Puzzle"])
        self.assertEqual([category["name"] for category in self.admin_client.get("/api/categories").json], ["Co-op", "Puzzle"])
        with Session(engine) as session:
            self.assertEqual(sorted(session.scalars(select(Category.name))), ["Co-op", "Puzzle"])
            self.assertIsNotNone(session.get(AppMigration, "category-inventory-v1"))
        with engine.connect() as connection:
            self.assertFalse(connection.exec_driver_sql(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'game_categories'"
            ).first())

    def test_theme_switch_is_on_every_page(self):
        _game_id, slug = self.create_game()
        for client, path in ((self.public_client, "/"), (self.public_client, f"/{slug}"), (self.admin_client, "/settings")):
            page = client.get(path).get_data(as_text=True)
            self.assertIn('<script src="/assets/js/theme.js"></script>', page.split("</head>")[0])
            self.assertEqual(page.count('name="theme"'), 2)
        with self.public_client.get("/assets/js/theme.js") as script:
            self.assertEqual(script.status_code, 200)

    def test_menu_links_can_have_their_own_icon(self):
        nav = [
            {"key": "link", "label": "Skjema", "url": "https://forms.example/", "icon": "clipboard"},
            {"key": "link", "label": "Ukjent", "url": "/vilkar", "icon": "<script>"},
        ]
        self.assertEqual(self.admin_client.put("/api/settings", json={"nav": nav}).status_code, 200)
        page = self.public_client.get("/").get_data(as_text=True)
        self.assertIn('icons.svg#clipboard"/></svg><span>Skjema</span>', page)
        self.assertIn('icons.svg#link"/></svg><span>Ukjent</span>', page)
        editor = json.loads(self.admin_client.get("/settings").get_data(as_text=True).split('id="settings-data">')[1].split("</script>")[0])
        self.assertIn("clipboard", editor["nav_icons"])
        self.assertEqual(editor["nav"][0]["icon"], "clipboard")
        # Links saved before icons could be chosen keep their old icon.
        with Session(self.admin.extensions["database_engine"]) as session:
            session.merge(Setting(key="nav", value=json.dumps([{"key": "link", "label": "Gammel", "url": "https://x.example/", "new_tab": True}])))
            session.commit()
        self.assertIn('icons.svg#external"/></svg><span>Gammel</span>', self.public_client.get("/").get_data(as_text=True))

    def test_files_can_be_added_as_links(self):
        game_id, slug = self.create_game()
        add = lambda **body: self.admin_client.post(f"/api/games/{game_id}/file-links", json=body)
        self.assertEqual(add(platform="windows", url="javascript:alert(1)").status_code, 400)
        self.assertEqual(add(platform="windows", url="").status_code, 400)
        self.assertEqual(add(platform="cover", url="https://x.example/a.zip").status_code, 400)
        self.assertEqual(self.admin_client.post("/api/games/999/file-links", json={"platform": "mac", "url": "https://x.example/"}).status_code, 404)
        named = add(platform="windows", url="https://cdn.example/builds/Spill%20Setup.zip")
        drive = add(platform="mac", url="https://www.drive.example/file/d/abc/view")
        self.assertEqual(named.status_code, 201, named.get_data(as_text=True))
        self.assertEqual((named.json["name"], named.json["href"]), ("Spill Setup.zip", "https://cdn.example/builds/Spill%20Setup.zip"))
        self.assertEqual(drive.json["name"], "drive.example")
        page = self.public_client.get(f"/{slug}").get_data(as_text=True)
        self.assertIn('<a class="download-btn" href="https://cdn.example/builds/Spill%20Setup.zip" target="_blank" rel="noopener noreferrer">', page)
        self.assertIn('icons.svg#external"/></svg><span class="file-name" title="Spill Setup.zip">', page)
        self.assertIn("Last ned og spill", page)
        self.assertEqual(self.admin_client.delete(f"/api/files/{drive.json['id']}").status_code, 200)
        self.assertEqual(len(self.admin_client.get(f"/api/games/{game_id}").json["files"]), 1)

    def test_newlines_in_text_become_line_breaks(self):
        from richtext import page_sections, rich_text

        self.assertEqual(str(rich_text("Linje 1\nLinje 2\n\nLinje 4\n")), "Linje 1<br>Linje 2<br><br>Linje 4")
        self.assertEqual(str(rich_text("Før<br>\nEtter")), "Før<br>Etter")
        self.assertEqual(str(rich_text("<ul>\n<li>a</li>\n</ul>\n\n<p>b</p>")), "<ul><li>a</li></ul><p>b</p>")
        self.assertEqual(str(rich_text("<b>Fet</b>\nlinje")), "<b>Fet</b><br>linje")
        page = page_sections("<h1>Tittel</h1>\n<p>Intro</p>\n\n<h2>Kort</h2>\nFørste\nAndre")
        self.assertEqual((str(page["intro"]), str(page["sections"][0]["body"])), ("<h1>Tittel</h1><p>Intro</p>", "Første<br>Andre"))
        _game_id, slug = self.create_game(note="Tips:\n\nHusk å lagre")
        self.assertIn("Tips:<br><br>Husk å lagre", self.public_client.get(f"/{slug}").get_data(as_text=True))

    def test_settings_reject_unsafe_menu_links(self):
        for url in ("javascript:alert(1)", "//evil.example", "", "#top"):
            response = self.admin_client.put("/api/settings", json={"nav": [{"key": "link", "label": "X", "url": url}]})
            self.assertEqual(response.status_code, 400, url)
        self.assertEqual(self.admin_client.put("/api/settings", json={"nav": "nope"}).status_code, 400)
        self.assertEqual(self.admin_client.put("/api/settings", json={"site_title": "x" * 101}).status_code, 400)
        response = self.admin_client.put("/api/settings", json={"nav": [{"key": "link", "label": "Side", "url": "/vilkar#ansvar"}]})
        self.assertEqual(response.status_code, 200)
        nav = self.public_client.get("/").get_data(as_text=True).split('class="site-nav"')[1].split("</nav>")[0]
        self.assertLess(nav.index("/vilkar#ansvar"), nav.index('href="/"'))

    def test_logo_is_used_as_brand_and_favicon(self):
        self.assertEqual(self.admin_client.post("/api/settings/logo", data=b"<svg/>").status_code, 400)
        first = self.admin_client.post("/api/settings/logo", data=PNG, content_type="application/octet-stream")
        self.assertEqual(first.status_code, 200, first.get_data(as_text=True))
        second = self.admin_client.post("/api/settings/logo", data=PNG, content_type="application/octet-stream")
        logo_url = second.json["logo_url"]
        page = self.public_client.get("/").get_data(as_text=True)
        self.assertIn(f'<link rel="icon" href="{logo_url}">', page)
        self.assertIn(f'<img class="brand-logo" src="{logo_url}"', page)
        with self.public_client.get(logo_url) as image:
            self.assertEqual((image.status_code, image.mimetype, image.data), (200, "image/png", PNG))
        self.assertEqual(self.public_client.get(first.json["logo_url"]).status_code, 404)
        self.assertEqual(len(list(Path(self.admin.config["SITE_DIR"]).iterdir())), 1)
        self.assertEqual(self.public_client.get("/favicon.ico").headers["Location"], logo_url)
        self.assertEqual(self.admin_client.delete("/api/settings/logo").status_code, 200)
        with self.public_client.get("/favicon.ico") as icon:
            self.assertEqual(icon.status_code, 200)
        self.assertIn('href="/assets/img/favicon.ico"', self.public_client.get("/").get_data(as_text=True))
        self.assertEqual(list(Path(self.admin.config["SITE_DIR"]).iterdir()), [])

    def test_install_and_terms_pages_can_be_rewritten(self):
        install = self.public_client.get("/install").get_data(as_text=True)
        self.assertIn('id="windows"', install)
        self.assertIn('href="#mac"', install)
        self.assertIn("Pakk ut alle", install)
        self.assertIn("privat bruk", self.public_client.get("/vilkar").get_data(as_text=True))
        custom = (
            "<h1>Egen veiledning</h1><p>Intro</p><script>alert(1)</script>"
            '<h2 data-icon="linux">Linux</h2><ol><li>Steg</li></ol>'
            '<h2 data-icon="evil">Annet</h2><p>Tekst</p><hr><p>Fotnote</p>'
        )
        self.assertEqual(self.admin_client.put("/api/settings", json={"install_content": custom}).status_code, 200)
        page = self.public_client.get("/install").get_data(as_text=True)
        self.assertIn("<h1>Egen veiledning</h1>", page)
        self.assertIn('<section class="guide-card rich" id="linux">', page)
        self.assertIn('href="#linux"', page)
        self.assertIn('id="annet"', page)
        self.assertIn("icons.svg#book", page)
        self.assertIn('class="guide-footnote rich"><p>Fotnote</p>', page)
        self.assertNotIn("alert(1)", page)
        self.assertNotIn("Pakk ut alle", page)
        default = self.admin_client.get("/settings").get_data(as_text=True)
        self.assertIn("Pakk ut alle", default)
        from pages import PAGES

        self.admin_client.put("/api/settings", json={"install_content": PAGES["install"]["default"]})
        with Session(self.admin.extensions["database_engine"]) as session:
            self.assertIsNone(session.get(Setting, "install_content"))
        self.assertIn("Pakk ut alle", self.public_client.get("/install").get_data(as_text=True))

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
        self.app = create_admin_app(Path(self.temp_dir.name) / "data", Path(self.temp_dir.name) / "games")
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
            app = create_admin_app(Path(self.temp_dir.name) / "open", Path(self.temp_dir.name) / "games")
        self.addCleanup(app.extensions["database_engine"].dispose)
        self.assertEqual(app.test_client().get("/api/games").status_code, 200)

    def login(self, client, password):
        return client.post("/login", data={"password": password})

    def test_password_can_be_changed_and_reset_to_the_environment_password(self):
        other = self.app.test_client()
        self.login(self.client, "hemmelig")
        self.login(other, "hemmelig")
        self.assertEqual(other.get("/api/games").status_code, 200)
        self.assertIn("ADMIN_PASSWORD", self.client.get("/settings").get_data(as_text=True))
        change = lambda **body: self.client.post("/api/settings/password", json=body)
        self.assertEqual(change(current="feil", password="nytt-passord").status_code, 403)
        self.assertEqual(change(current="hemmelig", password="kort").status_code, 400)
        self.assertEqual(change(current="hemmelig", password="nytt-passord").status_code, 200)
        self.assertEqual(self.client.get("/api/games").status_code, 200)
        self.assertEqual(other.get("/api/games").status_code, 401)
        self.assertEqual(self.login(other, "hemmelig").status_code, 401)
        self.assertEqual(self.login(other, "nytt-passord").status_code, 302)

        self.assertEqual(self.client.delete("/api/settings/password", json={"current": "hemmelig"}).status_code, 403)
        reset = self.client.delete("/api/settings/password", json={"current": "nytt-passord"})
        self.assertEqual((reset.status_code, reset.json["source"]), (200, "env"))
        self.assertEqual(self.client.get("/api/games").status_code, 200)
        self.assertEqual(other.get("/api/games").status_code, 401)
        self.assertEqual(self.login(other, "hemmelig").status_code, 302)
        self.assertEqual(self.client.delete("/api/settings/password", json={"current": "hemmelig"}).status_code, 400)

    def test_saving_a_password_without_environment_password_turns_on_login(self):
        with mock.patch.dict(os.environ, {"ADMIN_PASSWORD": ""}):
            app = create_admin_app(Path(self.temp_dir.name) / "open", Path(self.temp_dir.name) / "games")
        self.addCleanup(app.extensions["database_engine"].dispose)
        owner = app.test_client()
        self.assertEqual(owner.post("/api/settings/password", json={"password": "langt-passord"}).status_code, 200)
        self.assertEqual(owner.get("/api/games").status_code, 200)
        stranger = app.test_client()
        self.assertEqual(stranger.get("/").status_code, 302)
        self.assertEqual(stranger.post("/login", data={"password": "langt-passord"}).status_code, 302)
        self.assertIn("Logg ut", stranger.get("/").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
