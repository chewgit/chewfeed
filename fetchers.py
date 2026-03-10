from dataclasses import dataclass, field
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import calendar
from email.utils import parsedate_to_datetime
import html
import re
import time

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import feedparser
from urllib.parse import urljoin, urlparse

# For parsing "Month YYYY" strings into sortable dates
MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}
DATE_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b"
)


@dataclass
class Article:
    title: str
    url: str
    date: Optional[str] = None
    sort_date: Optional[datetime] = field(default=None, repr=False)
    paywalled: bool = False
    source_name: Optional[str] = None


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _format_feed_date(parsed_time) -> str:
    """Format feed timestamps using local date only."""
    if not parsed_time:
        return None
    # Feed times are often UTC; convert to local date to avoid off-by-one day.
    dt_local = datetime.fromtimestamp(calendar.timegm(parsed_time))
    return dt_local.strftime("%b %d, %Y")


def _scrape_pg_date(article: Article) -> Article:
    """Visit an individual PG essay page to extract 'Month YYYY' date."""
    try:
        resp = requests.get(article.url, headers=HEADERS, timeout=8)
        resp.raise_for_status()
        text = resp.text[:3000]  # date is always near the top
        m = DATE_RE.search(text)
        if m:
            month_name, year = m.group(1), int(m.group(2))
            month_num = MONTH_MAP[month_name.lower()]
            article.date = f"{month_name[:3]} {year}"
            article.sort_date = datetime(year, month_num, 1)
    except Exception:
        pass
    return article


def fetch_paul_graham() -> tuple[list[Article], Optional[str]]:
    """Fetch recent essays from paulgraham.com, including dates from each page."""
    try:
        resp = requests.get(
            "https://paulgraham.com/articles.html",
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        articles = []
        seen = set()
        for a_tag in soup.find_all("a"):
            href = a_tag.get("href", "")
            title = a_tag.get_text(strip=True)
            if (
                href.endswith(".html")
                and not href.startswith("http")
                and title
                and len(title) > 1
                and href not in seen
            ):
                seen.add(href)
                articles.append(Article(
                    title=title,
                    url=f"https://paulgraham.com/{href}",
                ))
            if len(articles) >= 20:
                break

        # Fetch dates from individual essay pages in parallel
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(_scrape_pg_date, a): a for a in articles}
            for future in as_completed(futures):
                future.result()

        # Sort by date descending; undated essays go last
        articles.sort(
            key=lambda a: a.sort_date or datetime.min,
            reverse=True,
        )

        return articles, None
    except Exception as e:
        return [], f"Failed to fetch Paul Graham essays: {e}"


def fetch_acx() -> tuple[list[Article], Optional[str]]:
    """Fetch recent posts from Astral Codex Ten RSS feed."""
    try:
        resp = requests.get(
            "https://www.astralcodexten.com/feed",
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)

        articles = []
        for entry in feed.entries[:20]:
            date_str = None
            sort_dt = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                date_str = time.strftime("%b %d, %Y", entry.published_parsed)
                sort_dt = datetime(*entry.published_parsed[:6])

            articles.append(Article(
                title=entry.get("title", "Untitled"),
                url=entry.get("link", ""),
                date=date_str,
                sort_date=sort_dt,
            ))

        return articles, None
    except Exception as e:
        return [], f"Failed to fetch Astral Codex Ten feed: {e}"


def fetch_matt_levine() -> tuple[list[Article], Optional[str]]:
    """Fetch recent Money Stuff articles from Bloomberg."""
    try:
        resp = requests.get(
            "https://www.bloomberg.com/opinion/authors/ARqpQk8bh9E/matthew-s-levine",
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        articles = []
        seen = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "/opinion/articles/" not in href:
                continue
            title = a_tag.get_text(strip=True)
            if not title or href in seen:
                continue
            seen.add(href)
            if not href.startswith("http"):
                href = f"https://www.bloomberg.com{href}"
            articles.append(Article(
                title=title,
                url=href,
                paywalled=True,
            ))
            if len(articles) >= 15:
                break

        if not articles:
            return [], "No articles found. Bloomberg may restrict automated access."
        return articles, None
    except requests.exceptions.HTTPError as e:
        return [], f"Bloomberg returned HTTP {e.response.status_code}. Content requires a subscription to access."
    except Exception as e:
        return [], f"Failed to fetch Matt Levine articles: {e}"


def _try_parse_rss(text: str) -> list[Article] | None:
    """Try to parse text as an RSS/Atom feed. Returns articles or None."""
    feed = feedparser.parse(text)
    if not feed.entries:
        return None
    articles = []
    for entry in feed.entries[:20]:
        date_str = None
        sort_dt = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            date_str = _format_feed_date(entry.published_parsed)
            sort_dt = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            date_str = _format_feed_date(entry.updated_parsed)
            sort_dt = datetime(*entry.updated_parsed[:6])
        articles.append(Article(
            title=entry.get("title", "Untitled"),
            url=entry.get("link", ""),
            date=date_str,
            sort_date=sort_dt,
        ))
    return articles


def _scrape_links(html: str, base_url: str) -> list[Article]:
    """Scrape article-like links from an HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    base_parsed = urlparse(base_url)
    base_host = (base_parsed.netloc or "").lower()
    base_path = base_parsed.path or "/"

    # Remove nav, footer, sidebar elements to reduce noise
    for tag in soup.find_all(["nav", "footer", "aside", "header"]):
        tag.decompose()

    articles = []
    seen = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        title = a_tag.get_text(strip=True)
        # Skip empty, short, or navigation-like links
        if not title or len(title) < 5 or len(title) > 200:
            continue
        # Skip anchors, javascript, mailto
        if href.startswith(("#", "javascript:", "mailto:")):
            continue
        full_url = urljoin(base_url, href)
        full_parsed = urlparse(full_url)
        full_host = (full_parsed.netloc or "").lower()

        title_l = title.lower()
        if title_l in {
            "finance", "visit website", "feed", "latest",
            "sign in", "sign up", "bookmarks", "trending",
            "get now", "home",
        }:
            continue
        if "inboxchat.ai" in full_url.lower():
            continue

        # Site-specific hardening for newsletter directories.
        if "newsletterhunt.com" in base_host and "/newsletters/" in base_path:
            if "/emails/" not in full_parsed.path:
                continue
            if title_l.endswith("by matt levine"):
                continue
            if "view in browser" in title_l:
                continue
            # Ignore giant summary blobs; keep concise post titles.
            if len(title) > 120:
                continue

        # Generic quality filters for article-ish links.
        if any(full_parsed.path.lower().startswith(p) for p in ["/categories/", "/users/", "/newsletters/"]):
            continue
        if full_host == base_host and full_parsed.path in {"/", "/feed", "/latest", "/trending"}:
            continue
        if len(title) < 8:
            continue

        if full_url in seen:
            continue
        seen.add(full_url)
        articles.append(Article(title=title, url=full_url))
        if len(articles) >= 20:
            break
    return articles


def _parse_relative_date_label(label: str) -> Optional[datetime]:
    """Convert labels like 'about 3 hours ago' / '2 days ago' to a date."""
    text = (label or "").strip().lower()
    if not text:
        return None

    now = datetime.now()
    m = re.search(r"(?:about\s+)?(\d+)\s+(hour|hours|day|days|week|weeks|month|months)\s+ago", text)
    if not m:
        return None

    qty = int(m.group(1))
    unit = m.group(2)
    if unit.startswith("hour"):
        return now
    if unit.startswith("day"):
        return now - timedelta(days=qty)
    if unit.startswith("week"):
        return now - timedelta(days=7 * qty)
    if unit.startswith("month"):
        return now - timedelta(days=30 * qty)
    return None


def _extract_newsletterhunt_srcdoc_date(srcdoc_html: str) -> Optional[str]:
    """Extract date from Newsletter Hunt embedded tracker token p=MMDDYYYY."""
    if not srcdoc_html:
        return None
    match = re.search(r"\bp=(\d{8})\b", srcdoc_html)
    if not match:
        return None
    token = match.group(1)
    try:
        month = int(token[:2])
        day = int(token[2:4])
        year = int(token[4:8])
        dt = datetime(year, month, day)
        return dt.strftime("%b %d, %Y")
    except Exception:
        return None


def _parse_newsletterhunt_listing(soup: BeautifulSoup, base_url: str) -> list[Article]:
    """Extract newsletter entries from Newsletter Hunt listing pages."""
    parsed = urlparse(base_url)
    if "newsletterhunt.com" not in (parsed.netloc or "").lower() or "/newsletters/" not in (parsed.path or ""):
        return []

    page_title = (soup.title.get_text(" ", strip=True) if soup.title else "").lower()
    page_title = page_title.split("|", 1)[0].strip()
    significant_tokens = [
        tok for tok in re.findall(r"[a-z0-9]+", page_title)
        if tok not in {"by", "the", "and", "for", "with", "newsletterhunt"}
    ]

    articles: list[Article] = []
    seen: set[str] = set()
    cards = soup.select("li.bg-white article")
    for card in cards:
        candidate_links = []
        for a_tag in card.find_all("a", href=True):
            href = a_tag.get("href", "")
            if "/emails/" not in href:
                continue
            title = a_tag.get_text(" ", strip=True)
            if not title or len(title) < 8 or len(title) > 140:
                continue
            if "view in browser" in title.lower():
                continue
            candidate_links.append((title, urljoin(base_url, href)))

        if not candidate_links:
            continue

        title_url = None
        if significant_tokens:
            for title, href in candidate_links:
                lower = title.lower()
                if any(tok in lower for tok in significant_tokens):
                    title_url = (title, href)
                    break
        if not title_url and significant_tokens:
            # Skip cards that do not match the target newsletter identity.
            continue
        if not title_url:
            title_url = candidate_links[0]

        title, full_url = title_url
        lower_title = title.lower()
        if lower_title in {"finance", "visit website", "visit site", "latest"}:
            continue
        if full_url in seen:
            continue
        seen.add(full_url)

        article = Article(title=title, url=full_url)
        time_tag = card.find("time")
        relative_label = time_tag.get_text(" ", strip=True) if time_tag else ""
        relative_dt = _parse_relative_date_label(relative_label)
        if relative_dt:
            article.sort_date = relative_dt
            article.date = relative_dt.strftime("%b %d, %Y")
        articles.append(article)

    return articles


def _enrich_article_dates(articles: list[Article], max_items: int = 12):
    """Best-effort date enrichment for scraped links lacking publish dates."""
    targets = [a for a in articles if not a.date and a.url][:max_items]
    if not targets:
        return

    def _fetch_date(article: Article) -> tuple[Article, Optional[str]]:
        try:
            resp = requests.get(article.url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            date_str = _extract_article_date(soup)
            return article, date_str
        except Exception:
            return article, None

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(_fetch_date, a) for a in targets]
        for future in futures:
            article, date_str = future.result()
            if date_str:
                article.date = date_str
                try:
                    article.sort_date = datetime.strptime(date_str, "%b %d, %Y")
                except Exception:
                    pass


def _common_feed_urls(url: str) -> list[str]:
    """Generate common RSS/Atom feed endpoint candidates for a site."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return []

    base = f"{parsed.scheme}://{parsed.netloc}"
    candidates = [
        urljoin(base, "/feed/"),
        urljoin(base, "/feed"),
        urljoin(base, "/rss"),
        urljoin(base, "/rss.xml"),
        urljoin(base, "/feed.xml"),
        urljoin(base, "/atom.xml"),
        urljoin(base, "/index.xml"),
    ]

    # If input is a subpath, also try path-specific feed endpoint first.
    stripped = url.rstrip("/")
    if parsed.path and parsed.path != "/":
        candidates.insert(0, f"{stripped}/feed/")

    deduped = []
    seen = set()
    for candidate in candidates:
        if candidate not in seen and candidate != url:
            seen.add(candidate)
            deduped.append(candidate)
    return deduped


def _extract_article_date(soup: BeautifulSoup) -> Optional[str]:
    """Extract and normalize a publish date from common metadata tags."""
    meta_patterns = [
        {"property": "article:published_time"},
        {"property": "og:published_time"},
        {"name": "pubdate"},
        {"name": "publish-date"},
        {"name": "date"},
        {"itemprop": "datePublished"},
    ]
    for pattern in meta_patterns:
        tag = soup.find("meta", attrs=pattern)
        if tag and tag.get("content"):
            raw = tag.get("content", "").strip()
            normalized = _normalize_date(raw)
            if normalized:
                return normalized

    time_tag = soup.find("time")
    if time_tag:
        raw = (time_tag.get("datetime") or time_tag.get_text(" ", strip=True) or "").strip()
        normalized = _normalize_date(raw)
        if normalized:
            return normalized

    return None


def _normalize_date(raw: str) -> Optional[str]:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        pass
    try:
        dt = parsedate_to_datetime(raw)
        return dt.strftime("%b %d, %Y")
    except Exception:
        pass
    # Last resort: return a trimmed readable string.
    return raw[:40]


def _pick_article_root(soup: BeautifulSoup) -> Tag:
    """Pick the most likely content root from the page."""
    strong_selectors = [
        "article",
        ".post-content",
        ".entry-content",
        ".article-content",
        ".post",
        "[itemprop='articleBody']",
        "main article",
    ]
    fallback_selectors = [
        "main article",
        "main",
        "[role='main']",
        ".content",
    ]

    def _best_for_selectors(selectors: list[str]) -> Optional[Tag]:
        best_candidate = None
        best_len = 0
        for selector in selectors:
            for candidate in soup.select(selector):
                if candidate.name in {"body", "html"}:
                    continue
                text_len = len(candidate.get_text(" ", strip=True))
                if text_len < 180:
                    continue
                if text_len > best_len:
                    best_candidate = candidate
                    best_len = text_len
        return best_candidate

    # First prefer true article containers; only then fall back to broad layout regions.
    for selector in strong_selectors:
        best = _best_for_selectors([selector])
        if best is not None:
            return best

    for selector in fallback_selectors:
        best = _best_for_selectors([selector])
        if best is not None:
            return best

    return soup.body or soup


def _sanitize_article_html(root: Tag, base_url: str) -> str:
    """Convert article HTML to a lightweight, safe subset for the reader panel."""
    for tag in root.select(
        "script,style,noscript,iframe,svg,canvas,form,button,nav,footer,aside"
    ):
        tag.decompose()

    out = BeautifulSoup("", "html.parser")
    container = out.new_tag("div")
    out.append(container)
    allowed = {
        "p", "h1", "h2", "h3", "h4", "h5", "h6",
        "ul", "ol", "li", "blockquote", "pre", "code",
        "em", "strong", "b", "i", "a", "br", "hr",
    }

    def convert(node):
        if isinstance(node, NavigableString):
            text = str(node)
            if not text.strip():
                return []
            return [out.new_string(text)]

        if not isinstance(node, Tag):
            return []

        name = node.name.lower()
        if name in {"img", "video", "audio", "picture", "source"}:
            return []

        children = []
        for child in node.children:
            children.extend(convert(child))

        if name not in allowed:
            return children

        mapped = {"b": "strong", "i": "em"}.get(name, name)
        new_tag = out.new_tag(mapped)
        if mapped == "a" and node.get("href"):
            new_tag["href"] = urljoin(base_url, node["href"])
            new_tag["target"] = "_blank"
            new_tag["rel"] = "noopener noreferrer"

        for child in children:
            new_tag.append(child)

        if mapped not in {"br", "hr"} and not new_tag.get_text(strip=True):
            return []
        return [new_tag]

    for child in root.children:
        for converted in convert(child):
            container.append(converted)

    html = str(container)
    if not container.get_text(strip=True):
        # Final fallback to plain text paragraphs.
        text = root.get_text("\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        fallback = "".join(f"<p>{line}</p>" for line in lines[:300])
        return fallback or "<p>No readable text found for this article.</p>"
    return html


def _extract_plain_text(root: Tag) -> str:
    """Extract plain text with lightweight structure for reader mode."""
    for tag in root.select(
        "script,style,noscript,iframe,svg,canvas,form,button,nav,footer,aside,header,img,video,audio,picture,source"
    ):
        tag.decompose()

    block_tags = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "pre")
    lines = []

    def _clean_text(text: str) -> str:
        text = text.replace("\xa0", " ")
        text = text.replace("\u200b", "")
        text = text.replace("\ufeff", "")
        return re.sub(r"[ \t\r\f\v]+", " ", text).strip()

    def _paragraphize_raw_text(raw_text: str) -> str:
        paragraphs = []
        current = ""

        for raw_line in raw_text.splitlines():
            line = _clean_text(raw_line)
            if not line:
                if current:
                    paragraphs.append(current)
                    current = ""
                continue

            if not current:
                current = line
                continue

            # Handle punctuation-only continuation lines and hard-wrapped hyphenation.
            if line[0] in ",.;:!?)]}":
                current += line
            elif current.endswith("-") and len(line) > 0 and line[0].isalnum():
                current = current[:-1] + line
            else:
                current += " " + line

        if current:
            paragraphs.append(current)

        return "\n\n".join(paragraphs)

    def _fallback_text_from_html(node: Tag) -> str:
        html = str(node)
        # Treat 2+ <br> tags as paragraph breaks; keep single <br> as inline spacing.
        html = re.sub(r"(?is)(<br\s*/?>\s*){2,}", "\n\n", html)
        html = re.sub(r"(?is)<br\s*/?>", " ", html)
        soup = BeautifulSoup(html, "html.parser")
        return _paragraphize_raw_text(soup.get_text("\n", strip=False))

    for tag in root.find_all(block_tags):
        # Keep leaf-like blocks to avoid repeating parent + child text.
        if tag.name != "li" and tag.find(block_tags, recursive=False):
            continue

        if tag.name == "pre":
            pre_lines = [line.rstrip() for line in tag.get_text("\n", strip=False).splitlines()]
            text = "\n".join(line for line in pre_lines if line.strip()).strip()
        else:
            separator = "\n" if tag.find("br") else " "
            text = _clean_text(tag.get_text(separator, strip=True))

        if not text:
            continue
        if tag.name == "li":
            text = f"- {text}"
        if lines and lines[-1] == text:
            continue
        lines.append(text)

    # Keep readability: single-spaced lines, with a blank line between blocks.
    extracted = "\n\n".join(lines)

    # If extracted text is suspiciously short, fall back to line-based body extraction.
    fallback_structured = _fallback_text_from_html(root)

    if not extracted:
        if not fallback_structured:
            return "No readable text found for this article."
        return fallback_structured[:120000]

    if fallback_structured:
        if len(extracted) < 700 or len(extracted) < int(len(fallback_structured) * 0.45):
            extracted = fallback_structured

    return extracted[:120000]


def _extract_reader_html(root: Tag) -> str:
    """Extract lightweight reader HTML that preserves bold emphasis only."""
    for tag in root.select(
        "script,style,noscript,iframe,svg,canvas,form,button,nav,footer,aside,header,img,video,audio,picture,source"
    ):
        tag.decompose()

    block_tags = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "pre")

    def _inline(node) -> str:
        if isinstance(node, NavigableString):
            return html.escape(str(node))
        if not isinstance(node, Tag):
            return ""

        name = node.name.lower()
        if name == "br":
            return "<br>"

        inner = "".join(_inline(child) for child in node.children)
        if name in {"strong", "b"}:
            text_only = BeautifulSoup(inner, "html.parser").get_text(" ", strip=True)
            if not text_only:
                return ""
            return f"<strong>{inner}</strong>"
        return inner

    blocks = []
    for tag in root.find_all(block_tags):
        if tag.name != "li" and tag.find(block_tags, recursive=False):
            continue

        if tag.name == "pre":
            pre_lines = [line.rstrip() for line in tag.get_text("\n", strip=False).splitlines()]
            pre_text = "\n".join(line for line in pre_lines if line.strip()).strip()
            if not pre_text:
                continue
            rendered = html.escape(pre_text).replace("\n", "<br>")
        else:
            rendered = "".join(_inline(child) for child in tag.children).strip()
            if tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                rendered = f"<strong>{rendered}</strong>"

        text_only = BeautifulSoup(rendered, "html.parser").get_text(" ", strip=True)
        if not text_only:
            continue
        if tag.name == "li":
            rendered = f'<span class="reader-bullet">- </span>{rendered}'
        blocks.append(rendered)

    if not blocks:
        fallback = html.escape(root.get_text("\n", strip=True))
        if not fallback:
            return "No readable text found for this article."
        return fallback.replace("\n\n", "<br><br>").replace("\n", " ")[:240000]

    return "<br><br>".join(blocks)[:240000]


def fetch_article_content(url: str) -> tuple[dict, Optional[str]]:
    """Fetch and extract a single article for the in-app reader."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        outer_soup = soup

        parsed = urlparse(url)

        # Newsletter Hunt email pages embed real newsletter HTML inside iframe[srcdoc].
        if "newsletterhunt.com" in (parsed.netloc or "").lower() and "/emails/" in (parsed.path or ""):
            iframe = soup.find("iframe", srcdoc=True)
            srcdoc = iframe.get("srcdoc", "") if iframe else ""
            if srcdoc:
                decoded = html.unescape(srcdoc)
                embedded_soup = BeautifulSoup(decoded, "html.parser")
                if embedded_soup.get_text(" ", strip=True):
                    soup = embedded_soup

            # Try to follow explicit "View in browser" external links when present.
            view_link = outer_soup.find("a", string=re.compile(r"view in browser", re.I))
            if view_link and view_link.get("href"):
                upstream = urljoin(url, view_link["href"])
                upstream_parsed = urlparse(upstream)
                if upstream_parsed.netloc and "newsletterhunt.com" not in upstream_parsed.netloc.lower():
                    try:
                        upstream_resp = requests.get(upstream, headers=HEADERS, timeout=15)
                        upstream_resp.raise_for_status()
                        soup = BeautifulSoup(upstream_resp.text, "html.parser")
                        url = upstream
                    except Exception:
                        pass

        title = None
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(" ", strip=True)
        if not title and soup.title:
            title = soup.title.get_text(" ", strip=True)
        if not title:
            title = "Untitled"
        if title.lower() in {"money stuff", "untitled"}:
            outer_h2 = outer_soup.find("h2")
            if outer_h2:
                outer_title = outer_h2.get_text(" ", strip=True)
                if outer_title:
                    title = outer_title
        if " | " in title:
            title = title.split(" | ", 1)[0].strip()

        article_date = _extract_article_date(soup)
        if not article_date and "newsletterhunt.com" in (parsed.netloc or "").lower():
            iframe = outer_soup.find("iframe", srcdoc=True)
            srcdoc = iframe.get("srcdoc", "") if iframe else ""
            article_date = _extract_newsletterhunt_srcdoc_date(html.unescape(srcdoc) if srcdoc else "")
            if not article_date:
                outer_time = outer_soup.find("time")
                if outer_time:
                    rel_dt = _parse_relative_date_label(outer_time.get_text(" ", strip=True))
                    if rel_dt:
                        article_date = rel_dt.strftime("%b %d, %Y")
        root = _pick_article_root(soup)
        # Clone selected content root so text/html extraction can clean independently.
        root_for_html = BeautifulSoup(str(root), "html.parser")
        root_for_text = BeautifulSoup(str(root), "html.parser")
        content_html = _extract_reader_html(root_for_html)
        # Preserve previous stable formatting path unless bold emphasis exists.
        if "<strong>" not in content_html:
            content_html = ""
        content_text = _extract_plain_text(root_for_text)
        return {
            "title": title,
            "date": article_date,
            "content_html": content_html,
            "content_text": content_text,
            "url": url,
        }, None
    except requests.exceptions.ConnectionError:
        return {}, f"Could not connect to {url}."
    except requests.exceptions.Timeout:
        return {}, f"Request to {url} timed out."
    except requests.exceptions.HTTPError as e:
        return {}, f"HTTP {e.response.status_code} from {url}."
    except Exception as e:
        return {}, f"Failed to fetch article: {e}"


def fetch_generic(url: str) -> tuple[list[Article], Optional[str]]:
    """Fetch articles from an arbitrary URL. Tries RSS first, then HTML scraping."""
    def _try_common_feed_candidates() -> list[Article] | None:
        for candidate_feed_url in _common_feed_urls(url):
            try:
                feed_resp = requests.get(
                    candidate_feed_url, headers=HEADERS, timeout=10
                )
                feed_resp.raise_for_status()
                parsed = _try_parse_rss(feed_resp.text)
                if parsed:
                    return parsed
            except Exception:
                continue
        return None

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        text = resp.text

        # 1. Try parsing response directly as RSS/Atom
        content_type = resp.headers.get("Content-Type", "")
        if "xml" in content_type or "rss" in content_type or "atom" in content_type:
            articles = _try_parse_rss(text)
            if articles:
                return articles, None

        # Even if content-type is html, it might be RSS (some servers misconfigure)
        articles = _try_parse_rss(text)
        if articles:
            return articles, None

        # 2. Look for RSS feed link in the HTML
        soup = BeautifulSoup(text, "html.parser")
        hunt_articles = _parse_newsletterhunt_listing(soup, url)
        if hunt_articles:
            hunt_articles.sort(key=lambda a: a.sort_date or datetime.min, reverse=True)
            return hunt_articles, None
        feed_link = soup.find("link", attrs={"type": re.compile(r"(rss|atom)")})
        if feed_link and feed_link.get("href"):
            feed_url = urljoin(url, feed_link["href"])
            try:
                feed_resp = requests.get(feed_url, headers=HEADERS, timeout=10)
                feed_resp.raise_for_status()
                articles = _try_parse_rss(feed_resp.text)
                if articles:
                    return articles, None
            except Exception:
                pass

        # 3. Probe common feed endpoints for blogs that do not expose feed
        # link tags in the homepage HTML.
        feed_articles = _try_common_feed_candidates()
        if feed_articles:
            return feed_articles, None

        # 4. Fallback: scrape article links from HTML
        articles = _scrape_links(text, url)
        if articles:
            # Scraped pages often miss explicit dates; enrich best-effort.
            _enrich_article_dates(articles)
            articles.sort(key=lambda a: a.sort_date or datetime.min, reverse=True)
            return articles, None

        return [], "No articles or feed found at this URL."
    except requests.exceptions.ConnectionError:
        return [], f"Could not connect to {url}."
    except requests.exceptions.Timeout:
        return [], f"Request to {url} timed out."
    except requests.exceptions.HTTPError as e:
        # Some sites rate-limit the homepage (HTTP 429) but still serve /feed/.
        if e.response is not None and e.response.status_code == 429:
            feed_articles = _try_common_feed_candidates()
            if feed_articles:
                return feed_articles, None
        return [], f"HTTP {e.response.status_code} from {url}."
    except Exception as e:
        return [], f"Failed to fetch: {e}"

