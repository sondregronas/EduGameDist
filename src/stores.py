"""Store metadata and automatic store-link discovery (Steam, GOG, itch.io, Humble Bundle)."""
import html
import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlparse


class FetchError(Exception):
    pass


STORES = (
    ("steampowered.com", "steam", "Steam"),
    ("gog.com", "gog", "GOG"),
    ("humblebundle.com", "humble", "Humble Bundle"),
    ("itch.io", "itch", "itch.io"),
    ("epicgames.com", "epic", "Epic Games"),
    ("play.google.com", "googleplay", "Google Play"),
    ("apps.apple.com", "appstore", "App Store"),
    ("itunes.apple.com", "appstore", "App Store"),
    ("nintendo.com", "nintendo", "Nintendo"),
    ("nintendo.no", "nintendo", "Nintendo"),
    ("github.com", "github", "GitHub"),
)


def store_info(url):
    host = (urlparse(url or "").hostname or "").lower().removeprefix("www.")
    for domain, key, label in STORES:
        if host == domain or host.endswith("." + domain):
            return {"key": key, "label": label}
    return {"key": "link", "label": host or str(url)}


def store_catalog():
    return [{"domain": domain, "key": key, "label": label} for domain, key, label in STORES]


def _is_store_url(url, domain):
    parsed = urlparse(url or "")
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host == domain or host.endswith("." + domain))


def normalize_title(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.casefold().replace("&", " and ")
    value = re.sub(r"[™®©]", "", value)
    value = re.sub(r"[^a-z0-9]+", "", value)
    return value


def _json(fetch, url):
    try:
        data, _content_type = fetch(url, max_bytes=2_000_000, accept="application/json")
        return json.loads(data.decode("utf-8"))
    except (FetchError, ValueError):
        raise FetchError("Ugyldig svar")


def steam_search(title, fetch):
    """Return the Steam app id of an exact title match, if there is one."""
    wanted = normalize_title(title)
    if not wanted:
        return None
    url = f"https://store.steampowered.com/api/storesearch/?term={quote(title)}&l=norwegian&cc=NO"
    payload = _json(fetch, url)
    for item in payload.get("items", []) if isinstance(payload, dict) else []:
        if (
            isinstance(item, dict)
            and item.get("type") == "app"
            and normalize_title(item.get("name")) == wanted
            and str(item.get("id", "")).isdigit()
        ):
            return str(item["id"])
    return None


def _find_gog(title, _developer, fetch):
    wanted = normalize_title(title)
    url = (
        "https://catalog.gog.com/v1/catalog?limit=10&productType=in%3Agame%2Cpack"
        f"&locale=en-US&query=like%3A{quote(title)}"
    )
    payload = _json(fetch, url)
    for item in payload.get("products", []) if isinstance(payload, dict) else []:
        if (
            isinstance(item, dict)
            and normalize_title(item.get("title")) == wanted
            and _is_store_url(item.get("storeLink"), "gog.com")
        ):
            return item["storeLink"]
    return None


ITCH_TITLE = re.compile(r'<a href="([^"]+)" class="title game_link"[^>]*>([^<]*)</a>')
ITCH_AUTHOR = re.compile(r'class="game_author"[^>]*><a[^>]*>([^<]*)</a>')


def _find_itch(title, developer, fetch):
    wanted = normalize_title(title)
    data, _ = fetch(f"https://itch.io/search?q={quote(title)}&type=games", max_bytes=2_000_000, accept="text/html")
    page = data.decode("utf-8", "replace")
    matches = []
    for segment in page.split('class="game_cell_data"')[1:]:
        title_match = ITCH_TITLE.search(segment)
        if not title_match:
            continue
        url, found_title = html.unescape(title_match.group(1)), html.unescape(title_match.group(2))
        if normalize_title(found_title) != wanted or not _is_store_url(url, "itch.io"):
            continue
        author_match = ITCH_AUTHOR.search(segment)
        author = html.unescape(author_match.group(1)) if author_match else ""
        matches.append((url, normalize_title(author)))
    if len(matches) == 1:
        return matches[0][0]
    wanted_developer = normalize_title(developer)
    if wanted_developer:
        for url, author in matches:
            if author and (author in wanted_developer or wanted_developer in author):
                return url
    return None


HUMBLE_TITLE = re.compile(r'<meta property="og:title" content="Buy (.+?) from the Humble Store"')


def _find_humble(title, _developer, fetch):
    wanted = normalize_title(title)
    base = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", title.replace("'", "")).encode("ascii", "ignore").decode().lower()).strip("-")
    slugs = [base] + ([base.removeprefix("the-")] if base.startswith("the-") else [])
    for slug in dict.fromkeys(slugs):
        if not slug:
            continue
        try:
            data, _ = fetch(f"https://www.humblebundle.com/store/{slug}", max_bytes=2_500_000, accept="text/html")
        except FetchError:
            continue
        match = HUMBLE_TITLE.search(data.decode("utf-8", "replace"))
        if match and normalize_title(html.unescape(match.group(1))) == wanted:
            return f"https://www.humblebundle.com/store/{slug}"
    return None


FINDERS = (_find_gog, _find_itch, _find_humble)


def discover_store_links(title, fetch, developer=""):
    """Look for the game on GOG, itch.io and Humble Bundle. Only exact title matches are returned."""
    title = (title or "").strip()
    if not title:
        return []

    def run(finder):
        try:
            return finder(title, developer, fetch)
        except (FetchError, ValueError, KeyError, TypeError):
            return None

    with ThreadPoolExecutor(max_workers=len(FINDERS)) as pool:
        urls = list(pool.map(run, FINDERS))
    return [{"url": url, **store_info(url)} for url in urls if url]
