"""Minimal allow-list HTML sanitizer for the teacher note."""
import html
from html.parser import HTMLParser
from urllib.parse import urlparse

from markupsafe import Markup

ALLOWED_TAGS = {"a", "b", "strong", "i", "em", "u", "small", "p", "br", "ul", "ol", "li"}
VOID_TAGS = {"br"}
SKIPPED_CONTENT = {"script", "style", "iframe", "object", "embed", "template"}
BREAKING_TAGS = {"br", "p", "ul", "ol", "li"}


def _safe_href(value):
    value = (value or "").strip()
    if value.startswith("/") and not value.startswith("//"):
        return value
    parsed = urlparse(value)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return value
    if parsed.scheme == "mailto" and parsed.path:
        return value
    return ""


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.open_tags = []
        self.skip_depth = 0
        self.after_break = True

    def handle_starttag(self, tag, attrs):
        if tag in SKIPPED_CONTENT:
            self.skip_depth += 1
            return
        if self.skip_depth or tag not in ALLOWED_TAGS:
            return
        if tag == "a":
            href = _safe_href(dict(attrs).get("href"))
            if not href:
                return
            self.out.append(f'<a href="{html.escape(href, quote=True)}" target="_blank" rel="noopener noreferrer">')
            self.open_tags.append("a")
            return
        self.out.append(f"<{tag}>")
        if tag not in VOID_TAGS:
            self.open_tags.append(tag)
        self.after_break = tag in BREAKING_TAGS

    def handle_startendtag(self, tag, attrs):
        if tag in VOID_TAGS:
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in SKIPPED_CONTENT:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth or tag not in self.open_tags:
            return
        while self.open_tags:
            current = self.open_tags.pop()
            self.out.append(f"</{current}>")
            if current == tag:
                break
        self.after_break = tag in BREAKING_TAGS

    def handle_data(self, data):
        if self.skip_depth:
            return
        for index, line in enumerate(data.replace("\r\n", "\n").split("\n")):
            if index:
                if not self.after_break:
                    self.out.append("<br>")
                self.after_break = True
            if line:
                self.out.append(html.escape(line))
                self.after_break = False

    def result(self):
        while self.open_tags:
            self.out.append(f"</{self.open_tags.pop()}>")
        return "".join(self.out).strip()


def rich_text(value):
    parser = _Sanitizer()
    parser.feed(str(value or ""))
    parser.close()
    return Markup(parser.result())
