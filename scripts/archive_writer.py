from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

GROUP_LABELS = {
    "news": "뉴스성 RSS",
    "tech_blog": "플랫폼·서비스 기술블로그",
    "ai_data": "AI·데이터 트렌드",
}


def _date_prefix(value: str) -> str:
    return (value or "")[:10]


def _today_kst() -> str:
    return datetime.now(KST).date().isoformat()


def _sort_key(item: dict) -> str:
    return item.get("published_at") or item.get("fetched_at") or ""


def _format_item(item: dict) -> str:
    source = item.get("source", "Unknown")
    title = item.get("title", "제목 없음")
    lines = [
        f"### [{source}] {title}",
        "",
        f"- 카테고리: {item.get('category', '')}",
        f"- 발행일: {item.get('published_at', '')}",
        f"- 수집일: {item.get('fetched_at', '')}",
        f"- 링크: {item.get('url', '')}",
        f"- 요약: {item.get('summary', '')}",
    ]
    if item.get("importance_score") is not None:
        lines.append(f"- 중요도: {item.get('importance_score')}")
    if item.get("planning_insight"):
        lines.append(f"- 기획 인사이트: {item.get('planning_insight')}")
    return "\n".join(lines)


def write_daily_archive(items: list[dict], output_dir: str = "docs/archive") -> None:
    archive_dir = Path(output_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)

    today = _today_kst()
    today_items = [
        item
        for item in items
        if _date_prefix(item.get("fetched_at", "")) == today
        or _date_prefix(item.get("published_at", "")) == today
    ]

    unique_items = {item.get("id"): item for item in today_items if item.get("id")}
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in sorted(unique_items.values(), key=_sort_key, reverse=True):
        grouped[item.get("group", "")].append(item)

    output_path = archive_dir / f"{today}.md"
    lines = [f"# {today} RSS 트렌드 브리핑 아카이브", ""]

    for group, label in GROUP_LABELS.items():
        lines.extend([f"## {label}", ""])
        group_items = grouped.get(group, [])
        if not group_items:
            lines.extend(["수집된 항목이 없습니다.", ""])
            continue
        for item in group_items:
            lines.extend([_format_item(item), ""])

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"  ✓ 아카이브 갱신: {output_path}")
