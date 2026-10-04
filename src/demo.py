import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app import create_admin_app, create_public_app
from database import Game, GameCategory, GameFile, GameStoreLink, category_named


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = Path(__file__).resolve().parent / "demo"
BASE = "/EduGameDist"

SAMPLES = [
    {
        "title": "Fake: Game",
        "description": "Explore the world of Fake: Game, a game about nothing.",
        "cover": "fakegame.png",
        "categories": ["Sample", "Adventure"],
        "players": "1",
        "time": "10 min",
        "files": [("windows", "Fake-Game-Windows.zip"), ("mac", "Fake-Game-Mac.zip")],
    },
    {
        "title": "Non-Existant",
        "description": "This game does not exist, nor do the associated links.",
        "cover": "nonexistant.png",
        "categories": ["Sample", "Game"],
        "players": "1",
        "time": "5 min",
        "files": [("linux", "Non-Existant-Linux.zip")],
    },
    {
        "title": "Oslo 2084",
        "description": (
            "I Oslo 2084 styrer spilleren Embla, en ung jente som bruker tiden sin på hobbyhacking og "
            "programmering av sin egen robotvenn, støvsugeren Moppy. I Oslo 2084 er byen i stadig større grad "
            "styrt av kunstig intelligens og ny teknologi. Embla og Moppy må løse ulike utfordringer og "
            "demokratiske dilemma for å bevege seg gjennom de ulike nivåene i spillet og kjempe mot "
            "anti-demokratiske krefter."
        ),
        "note": (
            "Fra Demokrativerksted hos Utøya (Europeiske Wergeland Centre).<br>"
            '<a href="https://theewc.org/content/uploads/sites/7/2021/10/Hefte-Oslo-2084-1-1.pdf">'
            "Trykk her for Ressurshefte.pdf</a>"
        ),
        "developer": "Anansi AS",
        "developer_link": "https://demokrativerksted.no/spill",
        "browser_url": "https://anansigames.itch.io/oslo2084",
        "links": ["https://anansigames.itch.io/oslo2084"],
        "cover": "oslo2084.png",
        "categories": ["Demokrati", "Norsk"],
        "players": "1",
        "time": "45 min",
        "files": [],
    },
    {
        "title": "Sample 2",
        "description": "This is a sample game.",
        "cover": "sample2.png",
        "categories": ["Sample", "Game"],
        "players": "1+",
        "time": "3 hours",
        "files": [("android", "Sample-2.apk")],
    },
    {
        "title": "Space Filler 3",
        "description": "A sample game filling the space of an otherwise empty library.",
        "cover": "spacefiller3.png",
        "categories": ["Space", "Sample"],
        "players": "2-8",
        "time": "30 min",
        "files": [],
    },
]


def _static_paths(html, slugs):
    pages = {"": "index.html", "install": "install.html", "vilkar": "vilkar.html"}
    pages.update({slug: f"{slug}.html" for slug in slugs})

    def href(match):
        path, fragment = match.group(1), match.group(2) or ""
        path, query = (path.split("?", 1) + [""])[:2]
        query = f"?{query}" if query else ""
        if path.startswith("assets/"):
            return f'href="{BASE}/{path}{fragment}"'
        if path.startswith("files/"):
            return 'href="#"'
        if path in pages:
            return f'href="{BASE}/{pages[path]}{query}{fragment}"'
        return match.group(0)

    html = re.sub(r'href="/([^"#]*)(#[^"]*)?"', href, html)
    html = html.replace('src="/assets/', f'src="{BASE}/assets/')
    html = html.replace('src="/EduGameDist/', f'src="{BASE}/')
    return html

def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(Path(__file__).parent / "public", OUTPUT / "assets", dirs_exist_ok=True)
    shutil.copytree(ROOT / ".github" / "workflows" / "demo-img", OUTPUT / "demo-img", dirs_exist_ok=True)
    slugs = []

    with tempfile.TemporaryDirectory() as data_dir:
        bootstrap = create_admin_app(data_dir)
        engine = bootstrap.extensions["database_engine"]
        with Session(engine) as session:
            for sample in SAMPLES:
                slug = re.sub(r"[^\w-]+", "-", sample["title"].lower()).strip("-")
                slugs.append(slug)
                game = Game(
                    title=sample["title"],
                    description=sample["description"],
                    note=sample.get("note"),
                    developer=sample.get("developer"),
                    developer_link=sample.get("developer_link"),
                    browser_url=sample.get("browser_url"),
                    cover_url=f"{BASE}/demo-img/{sample['cover']}",
                    players=sample["players"],
                    time=sample["time"],
                    slug=slug,
                )
                session.add(game)
                session.flush()
                game.categories = [
                    GameCategory(game_id=game.id, category_id=category_named(session, name, create=True).id, position=index)
                    for index, name in enumerate(sample["categories"])
                ]
                game.store_links = [
                    GameStoreLink(game_id=game.id, url=url, label=urlparse(url).hostname or url, position=index)
                    for index, url in enumerate(sample.get("links") or ["https://store.steampowered.com/"])
                ]
                for platform, filename in sample["files"]:
                    session.add(
                        GameFile(
                            game_id=game.id,
                            platform=platform,
                            original_name=filename,
                            url="#",
                        )
                    )
            session.commit()
        engine.dispose()

        app = create_public_app(data_dir)
        try:
            client = app.test_client()
            pages = [("", "index.html"), ("install", "install.html"), ("vilkar", "vilkar.html")]
            pages.extend((slug, f"{slug}.html") for slug in slugs)
            for route, filename in pages:
                response = client.get(f"/{route}")
                if response.status_code != 200:
                    raise RuntimeError(f"Could not render demo page {route or '/'}: {response.status_code}")
                html = _static_paths(response.get_data(as_text=True), slugs)
                (OUTPUT / filename).write_text(html, encoding="utf-8")
        finally:
            app.extensions["database_engine"].dispose()


if __name__ == "__main__":
    main()
