"""Minimal allow-list HTML sanitizer for teacher notes, the front page text and the editable pages.

Line breaks in the text become <br>, so plain text needs no HTML. Newlines that only separate block
tags (</p>, <li>, …) are ignored, as is the newline right after an explicit <br>.
"""
import html
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

from markupsafe import Markup

ALLOWED_TAGS = {"a", "b", "strong", "i", "em", "u", "small", "p", "br", "ul", "ol", "li"}
PAGE_TAGS = ALLOWED_TAGS | {"h1", "h2", "h3", "blockquote", "hr"}
VOID_TAGS = {"br", "hr"}
SKIPPED_CONTENT = {"script", "style", "iframe", "object", "embed", "template"}
BLOCK_TAGS = {"p", "ul", "ol", "li", "h1", "h2", "h3", "blockquote", "hr"}
# Icons an editable page may put in front of a section heading: <h2 data-icon="windows">.
PAGE_ICONS = {
    "windows", "mac", "linux", "android", "browser", "shield", "info", "clock", "book", "gamepad",
    "help", "download", "warning", "lock", "user", "users", "file", "package", "link", "external",
}
CALLOUT_OPEN = (
    '<div class="callout"><svg class="icon" aria-hidden="true" focusable="false">'
    '<use href="/assets/img/icons.svg#info"/></svg><div class="callout-text">'
)


def safe_href(value):
    value = (value or "").strip()
    if value.startswith("/") and not value.startswith("//"):
        return value
    if value.startswith("#") and len(value) > 1:
        return value
    parsed = urlparse(value)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return value
    if parsed.scheme == "mailto" and parsed.path:
        return value
    return ""


def anchor_id(text):
    value = re.sub(r"[^\w-]+", "-", text.strip().lower(), flags=re.UNICODE)
    return re.sub(r"-+", "-", value).strip("-") or "del"


class _Sanitizer(HTMLParser):
    def __init__(self, tags=ALLOWED_TAGS, sections=False):
        super().__init__(convert_charrefs=True)
        self.tags = tags
        self.sections = sections
        self.intro = []
        self.out = self.intro
        self.parts = []
        self.footer = None
        self.heading = None
        self.open_tags = []
        self.skip_depth = 0
        # Which upcoming newlines are layout rather than line breaks: "all" after a block tag, "one" after <br>.
        self.swallow = "all"

    def _after(self, tag):
        self.swallow = "all" if tag in BLOCK_TAGS else "one" if tag == "br" else None

    def handle_starttag(self, tag, attrs):
        if tag in SKIPPED_CONTENT:
            self.skip_depth += 1
            return
        if self.skip_depth or tag not in self.tags:
            return
        top_level = not self.open_tags and self.heading is None
        if self.sections and top_level and tag == "h2" and self.footer is None:
            icon = dict(attrs).get("data-icon")
            self.heading = {"html": [], "text": [], "icon": icon if icon in PAGE_ICONS else None, "body": []}
            self.parts.append(self.heading)
            self.out = self.heading["html"]
            self.swallow = "all"
            return
        if self.sections and top_level and tag == "hr":
            self.footer = self.out = []
            self.swallow = "all"
            return
        if tag == "a":
            href = safe_href(dict(attrs).get("href"))
            if not href:
                return
            external = not href.startswith(("/", "#"))
            target = ' target="_blank" rel="noopener noreferrer"' if external else ""
            self.out.append(f'<a href="{html.escape(href, quote=True)}"{target}>')
            self.open_tags.append("a")
            self.swallow = None
            return
        self.out.append(CALLOUT_OPEN if tag == "blockquote" and self.sections else f"<{tag}>")
        if tag not in VOID_TAGS:
            self.open_tags.append(tag)
        self._after(tag)

    def handle_startendtag(self, tag, attrs):
        if tag in VOID_TAGS:
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in SKIPPED_CONTENT:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        if self.heading is not None and tag == "h2" and not self.open_tags:
            self.out = self.heading["body"]
            self.heading = None
            self.swallow = "all"
            return
        if tag not in self.open_tags:
            return
        while self.open_tags:
            current = self.open_tags.pop()
            self.out.append("</div></div>" if current == "blockquote" and self.sections else f"</{current}>")
            if current == tag:
                break
        self._after(tag)

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.heading is not None:
            self.heading["text"].append(data)
        for index, line in enumerate(data.replace("\r\n", "\n").split("\n")):
            if index:
                if self.swallow == "one":
                    self.swallow = None
                elif self.swallow is None:
                    self.out.append("<br>")
            if line:
                self.out.append(html.escape(line))
                if line.strip():
                    self.swallow = None

    def close_all(self):
        while self.open_tags:
            current = self.open_tags.pop()
            self.out.append("</div></div>" if current == "blockquote" and self.sections else f"</{current}>")
        if self.heading is not None:
            self.heading["body"] = []
            self.heading = None

    def result(self):
        self.close_all()
        return _join(self.out)


def _join(chunks):
    """Join output, dropping line breaks left by trailing newlines."""
    return re.sub(r"(?:\s*<br>)+\s*$", "", "".join(chunks)).strip()


def rich_text(value):
    parser = _Sanitizer()
    parser.feed(str(value or ""))
    parser.close()
    return Markup(parser.result())


def page_sections(value):
    """Sanitize an editable page. Every top-level <h2> starts a card, and anything after a top-level <hr> becomes a footnote."""
    parser = _Sanitizer(PAGE_TAGS, sections=True)
    parser.feed(str(value or ""))
    parser.close()
    parser.close_all()
    used = set()
    sections = []
    for part in parser.parts:
        base = anchor_id("".join(part["text"]))
        anchor, suffix = base, 2
        while anchor in used:
            anchor, suffix = f"{base}-{suffix}", suffix + 1
        used.add(anchor)
        sections.append({
            "id": anchor,
            "icon": part["icon"] or (anchor if anchor in PAGE_ICONS else None),
            "heading": Markup(_join(part["html"])),
            "body": Markup(_join(part["body"])),
        })
    return {
        "intro": Markup(_join(parser.intro)),
        "sections": sections,
        "footer": Markup(_join(parser.footer or [])),
    }
