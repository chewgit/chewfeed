import json
import os
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urlparse

import webview

from fetchers import (
    Article, fetch_paul_graham, fetch_generic, fetch_article_content,
)
from renderer import render_html, render_loading

# Persistence path: %APPDATA%/ChewFeed/sources.json
APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
CONFIG_DIR = os.path.join(APPDATA, "ChewFeed")
CONFIG_FILE = os.path.join(CONFIG_DIR, "sources.json")
HIDDEN_BUILTINS_FILE = os.path.join(CONFIG_DIR, "hidden_builtins.json")
FAVOURITES_FILE = os.path.join(CONFIG_DIR, "favourites.json")

# Colors for custom cards (cycles through these)
CUSTOM_COLORS = [
    "#27ae60", "#e74c3c", "#1abc9c", "#f39c12",
    "#9b59b6", "#3498db", "#2ecc71", "#d35400",
]

# Built-in source definitions
BUILTIN_SOURCES = [
    {"key": "pg", "name": "Paul Graham", "color": "#e67e22",
     "url": "https://paulgraham.com/articles.html", "fetcher": "pg"},
    {"key": "matt", "name": "Matt Levine \u2014 Money Stuff", "color": "#2980b9",
     "url": "https://newsletterhunt.com/newsletters/money-stuff-by-matt-levine", "fetcher": "generic"},
    {"key": "jvns", "name": "Julia Evans", "color": "#8e44ad",
     "url": "https://jvns.ca/", "fetcher": "generic"},
    {"key": "pragmatic", "name": "Pragmatic Engineer", "color": "#16a085",
     "url": "https://blog.pragmaticengineer.com/", "fetcher": "generic"},
    {"key": "bits", "name": "Bits About Money", "color": "#c0392b",
     "url": "https://www.bitsaboutmoney.com/archive/", "fetcher": "generic"},
    {"key": "ftav", "name": "FT Alphaville", "color": "#2c7fb8",
     "url": "https://ftav.substack.com/", "fetcher": "generic"},
]

BUILTIN_FETCHERS = {
    "pg": fetch_paul_graham,
}

_LAST_NON_FAV_SOURCES: list[dict] = []


def _load_custom_sources() -> list[dict]:
    if not os.path.exists(CONFIG_FILE):
        return []
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            if not isinstance(raw, list):
                return []

            # Backward-compat migration for old saved cards.
            migrated = []
            for idx, source in enumerate(raw):
                if not isinstance(source, dict):
                    continue
                key = source.get("key") or f"custom-{idx}"
                name = source.get("name") or source.get("title") or "Untitled"
                url = source.get("url") or ""
                color = source.get("color") or CUSTOM_COLORS[idx % len(CUSTOM_COLORS)]
                migrated.append({
                    "key": key,
                    "name": name,
                    "url": url,
                    "color": color,
                })
            return migrated
    except Exception:
        return []


def _save_custom_sources(sources: list[dict]):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=2)


def _load_hidden_builtins() -> set[str]:
    if not os.path.exists(HIDDEN_BUILTINS_FILE):
        return set()
    try:
        with open(HIDDEN_BUILTINS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {str(item) for item in data}
    except Exception:
        pass
    return set()


def _save_hidden_builtins(keys: set[str]):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(HIDDEN_BUILTINS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(keys), f, indent=2)


def _load_favourites() -> set[str]:
    if not os.path.exists(FAVOURITES_FILE):
        return set()
    try:
        with open(FAVOURITES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {str(item) for item in data}
    except Exception:
        pass
    return set()


def _save_favourites(keys: set[str]):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(FAVOURITES_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(keys), f, indent=2)


def _next_color(custom_sources: list[dict]) -> str:
    used = {s.get("color") for s in custom_sources}
    for c in CUSTOM_COLORS:
        if c not in used:
            return c
    return CUSTOM_COLORS[len(custom_sources) % len(CUSTOM_COLORS)]


def _normalize_source_url(raw_url: str) -> str:
    """Accept shorthand domains (e.g. blog.samaltman.com) and normalize to URL."""
    url = (raw_url or "").strip()
    if not url:
        raise ValueError("URL is required")

    # If the user entered a bare domain/path, default to HTTPS.
    if "://" not in url:
        url = f"https://{url}"

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Please enter a valid website or feed URL")

    return url


def _article_sort_key(article: Article) -> datetime:
    if article.sort_date:
        return article.sort_date
    if article.date:
        try:
            return datetime.strptime(article.date, "%b %d, %Y")
        except Exception:
            pass
    return datetime.min


def _compose_sources_with_favourites(non_fav_sources: list[dict], favourites: set[str]) -> list[dict]:
    """Build render list with My Favourites first from already-fetched sources."""
    render_sources = []
    for src in non_fav_sources:
        cloned = dict(src)
        cloned["favoritable"] = bool(src.get("favoritable", True))
        cloned["favourited"] = src["key"] in favourites
        render_sources.append(cloned)

    existing_keys = {s["key"] for s in render_sources}
    cleaned_favourites = favourites.intersection(existing_keys)

    favourites_articles = []
    for src in render_sources:
        if src["key"] not in cleaned_favourites:
            continue
        for article in src.get("articles", []):
            favourites_articles.append(Article(
                title=article.title,
                url=article.url,
                date=article.date,
                sort_date=article.sort_date,
                paywalled=article.paywalled,
                source_name=src["name"],
            ))
    favourites_articles.sort(key=_article_sort_key, reverse=True)

    favourites_error = None
    if not cleaned_favourites:
        favourites_error = "Star cards to add them to My Favourites."
    elif not favourites_articles:
        favourites_error = "No recent posts available from favourite cards yet."

    favourites_card = {
        "key": "favourites",
        "name": "My Favourites",
        "color": "#f5b041",
        "url": "",
        "articles": favourites_articles[:300],
        "error": favourites_error,
        "badge": False,
        "removable": False,
        "favoritable": False,
        "favourited": True,
        "is_favourites": True,
        "show_source_name": True,
    }

    return [favourites_card] + render_sources


def _fetch_all() -> list[dict]:
    """Fetch all sources (built-in + custom) in parallel."""
    custom_sources = _load_custom_sources()
    hidden_builtins = _load_hidden_builtins()
    favourites = _load_favourites()
    visible_builtins = [s for s in BUILTIN_SOURCES if s["key"] not in hidden_builtins]
    results = {}

    def _fetch_builtin(src):
        fetcher_name = src["fetcher"]
        if fetcher_name == "generic":
            articles, error = fetch_generic(src["url"])
        else:
            fetcher = BUILTIN_FETCHERS[fetcher_name]
            articles, error = fetcher()
        return src["key"], articles, error

    def _fetch_custom(src):
        raw_url = src.get("url", "")
        try:
            normalized_url = _normalize_source_url(raw_url)
        except ValueError:
            return src["key"], [], f"Invalid URL: {raw_url}"

        articles, error = fetch_generic(normalized_url)
        return src["key"], articles, error

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = []
        for src in visible_builtins:
            futures.append(pool.submit(_fetch_builtin, src))
        for src in custom_sources:
            futures.append(pool.submit(_fetch_custom, src))
        for future in futures:
            key, articles, error = future.result()
            results[key] = (articles, error)

    render_sources = []
    for src in visible_builtins:
        articles, error = results.get(src["key"], ([], None))
        render_sources.append({
            "key": src["key"],
            "name": src["name"],
            "color": src["color"],
            "url": src["url"],
            "articles": articles,
            "error": error,
            "badge": src.get("badge", False),
            "removable": True,
            "favoritable": True,
            "favourited": src["key"] in favourites,
        })
    for src in custom_sources:
        articles, error = results.get(src["key"], ([], None))
        render_sources.append({
            "key": src["key"],
            "name": src["name"],
            "color": src["color"],
            "url": src["url"],
            "articles": articles,
            "error": error,
            "badge": False,
            "removable": True,
            "favoritable": True,
            "favourited": src["key"] in favourites,
        })

    global _LAST_NON_FAV_SOURCES
    _LAST_NON_FAV_SOURCES = [dict(s) for s in render_sources]

    existing_keys = {s["key"] for s in render_sources}
    cleaned_favourites = favourites.intersection(existing_keys)
    if cleaned_favourites != favourites:
        _save_favourites(cleaned_favourites)
    return _compose_sources_with_favourites(render_sources, cleaned_favourites)


class FeedApi:
    """Exposed to JS via js_api. Public methods become window.pywebviewApi.*"""

    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def add_source(self, title, url):
        """Called from JS bridge to add a custom source card."""
        normalized_title = (title or "").strip()
        normalized_url = _normalize_source_url(url)

        custom = _load_custom_sources()
        # Generate unique key
        idx = len(custom)
        existing_keys = {s["key"] for s in custom}
        key = f"custom-{idx}"
        while key in existing_keys:
            idx += 1
            key = f"custom-{idx}"

        color = _next_color(custom)
        custom.append({
            "key": key,
            "name": normalized_title,
            "url": normalized_url,
            "color": color,
        })
        _save_custom_sources(custom)
        self._refresh()
        return {"ok": True}

    def remove_source(self, key):
        """Called from JS: window.pywebviewApi.remove_source(key)"""
        if key == "favourites":
            return {"ok": True}

        custom = _load_custom_sources()
        if any(s["key"] == key for s in custom):
            custom = [s for s in custom if s["key"] != key]
            _save_custom_sources(custom)
        else:
            hidden_builtins = _load_hidden_builtins()
            builtin_keys = {s["key"] for s in BUILTIN_SOURCES}
            if key in builtin_keys:
                hidden_builtins.add(key)
                _save_hidden_builtins(hidden_builtins)

        favourites = _load_favourites()
        if key in favourites:
            favourites.remove(key)
            _save_favourites(favourites)

        self._refresh()
        return {"ok": True}

    def toggle_favourite(self, key):
        """Called from JS to toggle a source card as favourite."""
        if key == "favourites":
            return {"ok": True, "favourited": True}

        favourites = _load_favourites()
        if key in favourites:
            favourites.remove(key)
        else:
            favourites.add(key)
        _save_favourites(favourites)
        return {"ok": True, "favourited": key in favourites}

    def get_article(self, url, source_name=None, fallback_title=None):
        """Called from JS to fetch article content for the reader sidebar."""
        normalized_url = _normalize_source_url(url)
        data, error = fetch_article_content(normalized_url)
        if error:
            raise Exception(error)
        return {
            "ok": True,
            "source_name": (source_name or "").strip(),
            "title": data.get("title") or (fallback_title or "Untitled"),
            "date": data.get("date"),
            "content_html": data.get("content_html", ""),
            "content_text": data.get("content_text", ""),
            "url": data.get("url", normalized_url),
        }

    def open_external(self, url):
        """Called from JS to open the current reader URL in browser."""
        normalized_url = _normalize_source_url(url)
        webbrowser.open_new_tab(normalized_url)
        return {"ok": True}

    def refresh_all(self):
        """Called from JS to refresh all feeds."""
        self._refresh()
        return {"ok": True}

    def _refresh(self):
        sources = _fetch_all()
        html = render_html(sources)
        self._window.load_html(html)


api = FeedApi()


def load_content(window):
    """Runs on background thread and auto-refreshes all feeds on app open."""
    api._refresh()


def main():
    window = webview.create_window(
        title="ChewFeed",
        html=render_loading(),
        width=1280,
        height=750,
        min_size=(800, 500),
        js_api=api,
    )
    api.set_window(window)
    webview.start(load_content, window)


if __name__ == "__main__":
    main()
