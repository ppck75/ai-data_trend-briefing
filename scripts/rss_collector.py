from __future__ import annotations

import hashlib
import html
import re
from calendar import timegm
from datetime import datetime
from email.utils import parsedate_to_datetime
from time import struct_time
from urllib.request import Request, urlopen
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import feedparser

KST = ZoneInfo("Asia/Seoul")
SUMMARY_LIMIT = 500
XML_ENTITY_NAMES = {"amp", "lt", "gt", "apos", "quot"}
PRESERVED_QUERY_PARAMS = {"no", "article_id", "articleId", "aid", "idx", "id"}


def now_kst() -> datetime:
    return datetime.now(KST)


def clean_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlsplit(url.strip())
        preserved_params = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=False)
            if key in PRESERVED_QUERY_PARAMS
        ]
        query = urlencode(preserved_params)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))
    except Exception:
        return url.strip().split("#", 1)[0].split("?", 1)[0]


def make_stable_id(url: str, title: str) -> str:
    seed = f"{clean_url(url)}|{title.strip()}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def clean_summary(value: str, limit: int = SUMMARY_LIMIT) -> str:
    text = value or ""
    text = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", " ", text, flags=re.I)
    text = re.sub(r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def sanitize_feed_xml(text: str) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)

    def replace_named_entity(match: re.Match) -> str:
        name = match.group(1)
        if name in XML_ENTITY_NAMES:
            return match.group(0)
        return html.unescape(match.group(0))

    return re.sub(r"&([A-Za-z][A-Za-z0-9]+);", replace_named_entity, text)


def parse_feed_with_fallback(url: str):
    feed = feedparser.parse(url)
    if getattr(feed, "entries", None):
        return feed

    try:
        request = Request(url, headers={"User-Agent": "rss-trend-briefing/1.0"})
        with urlopen(request, timeout=20) as response:
            raw = response.read()
        encoding = getattr(feed, "encoding", None) or "utf-8"
        text = raw.decode(encoding, errors="replace")
        cleaned_text = sanitize_feed_xml(text)
        fallback_feed = feedparser.parse(cleaned_text)
        if getattr(fallback_feed, "entries", None):
            return fallback_feed
    except Exception:
        return feed

    return feed


def parse_entry_datetime(entry: dict, key: str) -> str:
    raw_value = entry.get(key) or ""
    parsed_key = f"{key}_parsed"
    parsed_struct = entry.get(parsed_key)

    try:
        if isinstance(parsed_struct, struct_time):
            dt = datetime.fromtimestamp(timegm(parsed_struct), tz=KST)
            return dt.isoformat()
    except Exception:
        pass

    if raw_value:
        try:
            dt = parsedate_to_datetime(raw_value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=KST)
            return dt.astimezone(KST).isoformat()
        except Exception:
            return raw_value

    return ""


def collect_feed(feed_config: dict) -> list[dict]:
    source_name = feed_config.get("name", "Unknown")
    url = feed_config.get("url", "")
    max_items = int(feed_config.get("max_items", 10) or 10)

    if not url:
        print(f"  ✗ {source_name}: RSS URL이 비어 있습니다.")
        return []

    try:
        feed = parse_feed_with_fallback(url)
        if getattr(feed, "bozo", False):
            bozo_error = getattr(feed, "bozo_exception", "unknown parse error")
            print(f"  ! {source_name}: RSS 파싱 경고 - {bozo_error}")

        entries = getattr(feed, "entries", []) or []
        fetched_at = now_kst().isoformat()
        items: list[dict] = []

        for entry in entries[:max_items]:
            title = (entry.get("title") or "").strip()
            link = clean_url(entry.get("link") or entry.get("id") or "")
            if not title and not link:
                continue

            summary = clean_summary(entry.get("summary") or entry.get("description") or "")
            published_at = parse_entry_datetime(entry, "published")
            updated_at = parse_entry_datetime(entry, "updated")

            items.append(
                {
                    "id": make_stable_id(link, title),
                    "source": source_name,
                    "group": feed_config.get("group", ""),
                    "category": feed_config.get("category", ""),
                    "icon": feed_config.get("icon", ""),
                    "title": title,
                    "summary": summary,
                    "url": link,
                    "published_at": published_at or updated_at,
                    "entry_updated_at": updated_at,
                    "fetched_at": fetched_at,
                    "language": feed_config.get("language", ""),
                    "importance_weight": feed_config.get("importance_weight", 1.0),
                    "importance_score": None,
                    "keywords": [],
                    "planning_insight": "",
                }
            )

        print(f"  ✓ {source_name}: {len(items)}건 수집")
        return items
    except Exception as exc:
        print(f"  ✗ {source_name}: 수집 실패 - {exc}")
        return []
