"""Site settings that admins change under Settings. Stored as key/value rows in the `settings` table."""
import json

from flask import current_app, g
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from database import Setting
from pages import PAGES
from richtext import safe_href

DEFAULT_HERO_TEXT = "Get your game on"
BUILTIN_NAV = {
    "games": {"label": "Spill", "href": "/", "icon": "gamepad"},
    "install": {"label": "Installasjon", "href": "/install", "icon": "book"},
    "terms": {"label": "Vilkår", "href": "/vilkar", "icon": "shield"},
}
# Icons a custom menu link can have; the settings page cycles through them in this order.
NAV_ICONS = (
    "link", "external", "home", "school", "book", "clipboard", "email", "message", "calendar",
    "star", "heart", "info", "help", "gamepad", "users", "download",
)
MAX_NAV_LINKS = 20
MAX_NAV_LABEL = 40
TEXT_FIELDS = {
    "site_title": ("Tittelen", 100),
    "hero_title": ("Overskriften", 200),
    "hero_text": ("Teksten på forsiden", 2000),
    "install_content": ("Installasjonsveiledningen", 100_000),
    "terms_content": ("Vilkårene", 100_000),
}
# These fall back to their defaults when they are left empty.
OPTIONAL_FIELDS = {"site_title", "hero_title", "install_content", "terms_content"}
PAGE_FIELDS = {"install": "install_content", "terms": "terms_content"}


def _stored():
    if "db" not in g:
        return {}
    if "settings" not in g:
        try:
            g.settings = {row.key: row.value for row in g.db.scalars(select(Setting))}
        except SQLAlchemyError:
            # The public app can start before the admin app has created the table.
            g.db.rollback()
            g.settings = {}
    return g.settings


def get(key, default=""):
    return _stored().get(key, default)


def put(values):
    """Store settings. A value of None removes the setting so its default applies again."""
    stored = _stored()
    for key, value in values.items():
        row = g.db.get(Setting, key)
        if value is None:
            if row:
                g.db.delete(row)
            stored.pop(key, None)
        else:
            if row:
                row.value = value
            else:
                g.db.add(Setting(key=key, value=value))
            stored[key] = value
    g.db.flush()
    g.pop("site", None)


def site():
    """Everything the templates need to know about the site (title, logo, menu and front page)."""
    if "site" not in g:
        stored = _stored()
        title = stored.get("site_title") or current_app.config["TITLE"]
        logo = stored.get("logo", "")
        g.site = {
            "title": title,
            "hero_title": stored.get("hero_title") or title,
            "hero_text": stored.get("hero_text", DEFAULT_HERO_TEXT),
            "logo": logo,
            "logo_url": f"/logo/{logo}" if logo else "",
            "favicon_url": f"/logo/{logo}" if logo else "/assets/img/favicon.ico",
            "nav": nav_items(stored.get("nav")),
        }
    return g.site


def page_content(name):
    return get(PAGE_FIELDS[name]) or PAGES[name]["default"]


def _builtin_item(key, label="", hidden=False):
    builtin = BUILTIN_NAV[key]
    return {
        "key": key,
        "label": label,
        "text": label or builtin["label"],
        "href": builtin["href"],
        "icon": builtin["icon"],
        "hidden": hidden,
        "new_tab": False,
        "builtin": True,
    }


def nav_items(value):
    """The menu in display order. Built-in pages missing from the stored menu are added at the end."""
    try:
        stored = json.loads(value) if value else []
    except (TypeError, ValueError):
        stored = []
    items = []
    seen = set()
    for entry in stored if isinstance(stored, list) else []:
        if not isinstance(entry, dict):
            continue
        key = entry.get("key")
        label = str(entry.get("label") or "").strip()[:MAX_NAV_LABEL]
        if key in BUILTIN_NAV and key not in seen:
            seen.add(key)
            items.append(_builtin_item(key, label, bool(entry.get("hidden"))))
        elif key == "link":
            url = safe_href(str(entry.get("url") or ""))
            if not url or not label:
                continue
            new_tab = bool(entry.get("new_tab"))
            icon = entry.get("icon")
            items.append({
                "key": "link",
                "label": label,
                "text": label,
                "url": url,
                "href": url,
                "icon": icon if icon in NAV_ICONS else "external" if new_tab else "link",
                "hidden": False,
                "new_tab": new_tab,
                "builtin": False,
            })
    items.extend(_builtin_item(key) for key in BUILTIN_NAV if key not in seen)
    return items


def _validated_nav(entries):
    if not isinstance(entries, list) or len(entries) > MAX_NAV_LINKS + len(BUILTIN_NAV):
        raise ValueError("Menyen er ugyldig.")
    result = []
    seen = set()
    links = 0
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Menyen er ugyldig.")
        key = entry.get("key")
        label = str(entry.get("label") or "").strip()
        if len(label) > MAX_NAV_LABEL:
            raise ValueError(f"Navn i menyen kan ikke være lengre enn {MAX_NAV_LABEL} tegn.")
        if key in BUILTIN_NAV and key not in seen:
            seen.add(key)
            result.append({"key": key, "label": label, "hidden": bool(entry.get("hidden"))})
        elif key == "link":
            url = str(entry.get("url") or "").strip()
            if not label:
                raise ValueError("Alle lenker i menyen må ha et navn.")
            if len(url) > 2000 or url.startswith("#") or not safe_href(url):
                raise ValueError(f"Lenken «{label}» må starte med https://, http://, mailto: eller /.")
            links += 1
            icon = entry.get("icon") if entry.get("icon") in NAV_ICONS else "link"
            result.append({"key": "link", "label": label, "url": url, "new_tab": bool(entry.get("new_tab")), "icon": icon})
        else:
            raise ValueError("Menyen er ugyldig.")
    if links > MAX_NAV_LINKS:
        raise ValueError(f"Menyen kan ha maks {MAX_NAV_LINKS} egne lenker.")
    result.extend({"key": key, "label": "", "hidden": False} for key in BUILTIN_NAV if key not in seen)
    return result


def validate(body):
    """Validate the settings present in the request. Raises ValueError with a message for the admin."""
    values = {}
    for key, (label, limit) in TEXT_FIELDS.items():
        if key in body:
            value = str(body.get(key) or "").strip()
            if len(value) > limit:
                raise ValueError(f"{label} er for lang.")
            values[key] = None if key in OPTIONAL_FIELDS and not value else value
    for name, key in PAGE_FIELDS.items():
        # Keep following the built-in text (and its future updates) when it is saved unchanged.
        if values.get(key) and values[key] == PAGES[name]["default"].strip():
            values[key] = None
    if "nav" in body:
        values["nav"] = json.dumps(_validated_nav(body.get("nav")), ensure_ascii=False)
    return values


def editor_data():
    stored = _stored()
    current = site()
    return {
        "site_title": stored.get("site_title", ""),
        "hero_title": stored.get("hero_title", ""),
        "hero_text": stored.get("hero_text", DEFAULT_HERO_TEXT),
        "logo_url": current["logo_url"],
        "nav": [
            {key: item[key] for key in ("key", "label", "hidden", "url", "new_tab", "icon") if key in item}
            for item in current["nav"]
        ],
        "builtins": BUILTIN_NAV,
        "nav_icons": NAV_ICONS,
        "pages": {
            name: {"content": stored.get(key, ""), "default": PAGES[name]["default"]}
            for name, key in PAGE_FIELDS.items()
        },
    }
