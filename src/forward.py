"""Send browsers that have used admin straight to admin when they open the public site.

Admin and the public site have different addresses, so admin cannot set a cookie for the public site
directly. Instead admin.js sends the browser once through /admin-forward on the public site, which sets a
long-lived cookie there and sends the browser straight back. From then on the public site redirects that
browser to the same page in admin. Visitors who have never used admin are not affected.

The admin address is saved by admin itself (from the browser's Origin header). It is never taken from the
cookie or the link, so the redirect cannot be pointed at another site.
"""
import hmac
import secrets
from urllib.parse import urlencode, urlparse

from flask import current_app, jsonify, redirect, request

import settings

TOKEN = "forward_token"
ADMIN_ORIGIN = "admin_origin"
PATH = "/admin-forward"
COOKIE = "edugame_admin_forward"
# Set by "Åpne nettsiden" in admin, so admins can still look at the public site for a while.
PUBLIC_VIEW_COOKIE = "edugame_public_view"
PUBLIC_VIEW_PARAM = "public"
COOKIE_DAYS = 400  # The longest browsers keep a cookie.
PUBLIC_VIEW_HOURS = 3
PAGES = {"index", "game_page", "installation_guide", "terms"}


def _matches(value, expected):
    return bool(expected) and hmac.compare_digest(str(value or "").encode("utf-8"), expected.encode("utf-8"))


def _safe_path(value):
    value = str(value or "/")
    if not value.startswith("/") or value.startswith("//") or "\\" in value or len(value) > 2000:
        return "/"
    return value


def _no_store(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def public_base(public_url):
    return public_url.split("?")[0].split("#")[0].rstrip("/")


def public_view_url(public_url):
    return f"{public_base(public_url)}/?{PUBLIC_VIEW_PARAM}=1"


def configure_public(app):
    @app.before_request
    def forward_admins():
        if request.endpoint not in PAGES or request.method not in ("GET", "HEAD"):
            return None
        if PUBLIC_VIEW_PARAM in request.args or request.cookies.get(PUBLIC_VIEW_COOKIE):
            return None
        origin = settings.get(ADMIN_ORIGIN)
        if not origin or not _matches(request.cookies.get(COOKIE), settings.get(TOKEN)):
            return None
        return _no_store(redirect(origin + request.full_path.rstrip("?")))

    @app.after_request
    def remember_public_view(response):
        if request.endpoint in PAGES and PUBLIC_VIEW_PARAM in request.args:
            response.set_cookie(PUBLIC_VIEW_COOKIE, "1", max_age=PUBLIC_VIEW_HOURS * 60 * 60, httponly=True, samesite="Lax")
        return response

    @app.get(PATH)
    def admin_forward():
        origin = settings.get(ADMIN_ORIGIN)
        back = origin + _safe_path(request.args.get("back")) if origin else "/"
        if "off" in request.args:
            response = _no_store(redirect(back))
            response.delete_cookie(COOKIE)
            return response
        token = settings.get(TOKEN)
        if not origin or not _matches(request.args.get("token"), token):
            return _no_store(redirect("/"))
        response = _no_store(redirect(back))
        response.set_cookie(COOKIE, token, max_age=COOKIE_DAYS * 24 * 60 * 60, httponly=True, samesite="Lax")
        response.delete_cookie(PUBLIC_VIEW_COOKIE)
        return response


def configure_admin(app):
    @app.post("/api/public-forward")
    def public_forward():
        """Remember this admin address and return the links that turn forwarding on or off in this browser."""
        origin = request.headers.get("Origin", "")
        parsed = urlparse(origin)
        # The request guard has already checked that the Origin is this site.
        if parsed.scheme not in ("http", "https") or not parsed.netloc or origin != f"{parsed.scheme}://{parsed.netloc}":
            return jsonify(error="Nettleseren sendte ikke adressen til admin."), 400
        body = request.get_json(silent=True) or {}
        token = settings.get(TOKEN) or secrets.token_urlsafe(32)
        settings.put({TOKEN: token, ADMIN_ORIGIN: origin})
        base = public_base(current_app.config["PUBLIC_URL"])
        back = _safe_path(body.get("back"))
        return jsonify(
            on=f"{base}{PATH}?{urlencode({'token': token, 'back': back})}",
            off=f"{base}{PATH}?{urlencode({'off': '1', 'back': back})}",
            health=f"{base}/health",
            same_site=urlparse(base).netloc == parsed.netloc,
        )
