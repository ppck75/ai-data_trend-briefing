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
    if output_path.exists():
        existing_text = output_path.read_text(encoding="utf-8", errors="ignore")
        if existing_text.startswith("# 오늘의 RSS 트렌드 브리핑"):
            print(f"  ℹ 브리핑 아카이브가 있어 RSS 원자료 아카이브 덮어쓰기를 건너뜁니다: {output_path}")
            return

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


def _join_list(values: list[str] | None) -> str:
    return ", ".join(values or [])


def _briefing_item_block(item: dict, score_key: str, reason_key: str = "score_reason") -> list[str]:
    title = item.get("title", "제목 없음")
    lines = [
        f"### {item.get('rank', '-')}. {title}",
        "",
        f"- 출처: {item.get('source', '')}",
        f"- 점수: {item.get(score_key, '')}",
        f"- 핵심 키워드: {_join_list(item.get('keywords'))}",
        f"- 선정 이유: {item.get(reason_key, '')}",
        f"- 콘텐츠 전략 인사이트: {item.get('planning_insight', '')}",
        f"- 원문 링크: {item.get('url', '')}",
        "",
    ]
    return lines


def write_briefing_archive(briefing: dict, output_dir: str = "docs/archive") -> None:
    archive_dir = Path(output_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)

    briefing_date = briefing.get("briefing_date") or _today_kst()
    output_path = archive_dir / f"{briefing_date}.md"

    lines = [
        "# 오늘의 RSS 트렌드 브리핑",
        "",
        f"생성 시각: {briefing.get('generated_at', '')}  ",
        f"수집 항목 수: {briefing.get('source_total', 0)}개",
        "",
        "---",
        "",
        "## 오늘의 통합 Top 5",
        "",
    ]

    integrated_top5 = briefing.get("integrated_top5", [])
    if not integrated_top5:
        lines.extend(["선정된 항목이 없습니다.", ""])
    for item in integrated_top5:
        lines.extend(
            [
                f"### {item.get('rank', '-')}. {item.get('title', '제목 없음')}",
                "",
                f"- 출처: {item.get('source', '')}",
                f"- group: {item.get('group', '')}",
                f"- 통합 점수: {item.get('integrated_score', '')}",
                f"- 적용 기준: {_join_list(item.get('applied_criteria'))}",
                f"- 핵심 키워드: {_join_list(item.get('keywords'))}",
                f"- 한 줄 요약: {item.get('one_line_summary', '')}",
                f"- 왜 중요한가: {item.get('importance_reason', '')}",
                f"- 콘텐츠 전략 인사이트: {item.get('planning_insight', '')}",
                f"- 원문 링크: {item.get('url', '')}",
                "",
            ]
        )

    sections = [
        ("news", "뉴스성 RSS Top 5"),
        ("tech_blog", "플랫폼·서비스 기술블로그 Top 5"),
        ("ai_data", "AI·데이터 트렌드 Top 5"),
    ]
    category_top5 = briefing.get("category_top5", {})
    for group, title in sections:
        lines.extend(["---", "", f"## {title}", ""])
        items = category_top5.get(group, [])
        if not items:
            lines.extend(["선정된 항목이 없습니다.", ""])
            continue
        for item in items:
            lines.extend(_briefing_item_block(item, score_key="category_score"))

    lines.extend(["---", "", "## 오늘 반복 등장한 키워드", ""])
    lines.extend(["| 키워드 | 등장 횟수 | 관련 group | 관련 출처 |", "|---|---:|---|---|"])
    for keyword in briefing.get("hot_keywords", []):
        lines.append(
            f"| {keyword.get('keyword', '')} | {keyword.get('count', 0)} | "
            f"{_join_list(keyword.get('groups'))} | {_join_list(keyword.get('sources'))} |"
        )

    lines.extend(["", "---", "", "## 오늘 전체 흐름 요약", ""])
    for summary in briefing.get("overall_summary", []):
        lines.append(f"- {summary}")

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"  ✓ 브리핑 아카이브 갱신: {output_path}")
