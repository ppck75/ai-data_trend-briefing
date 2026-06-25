from __future__ import annotations

import json
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
    print("  ℹ 전체 RSS 원자료 아카이브는 저장하지 않습니다. 최신 200개는 docs/data.json에서만 유지합니다.")


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


def _parse_generated_at(value: str) -> datetime:
    if not value:
        return datetime.now(KST)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=KST)
        return dt.astimezone(KST)
    except Exception:
        return datetime.now(KST)


def _archive_paths(briefing: dict, output_dir: str) -> tuple[Path, Path, Path, str, str]:
    generated_at = _parse_generated_at(briefing.get("generated_at", ""))
    date_key = briefing.get("briefing_date") or generated_at.date().isoformat()
    time_key = generated_at.strftime("%H-%M")
    archive_dir = Path(output_dir)
    day_dir = archive_dir / date_key
    return day_dir / f"{time_key}.md", day_dir / f"{time_key}.json", archive_dir / "index.json", date_key, time_key


def _load_archive_index(index_path: Path) -> dict:
    if not index_path.exists():
        return {"updated_at": "", "archives": []}
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
        if not isinstance(data.get("archives"), list):
            data["archives"] = []
        return data
    except Exception:
        return {"updated_at": "", "archives": []}


def _archive_index_entry(briefing: dict, date_key: str, time_key: str) -> dict:
    hot_keywords = [item.get("keyword", "") for item in briefing.get("hot_keywords", []) if item.get("keyword")]
    integrated_titles = [
        item.get("title", "")
        for item in briefing.get("integrated_top5", [])
        if item.get("title")
    ][:5]
    return {
        "id": f"{date_key}_{time_key}",
        "date": date_key,
        "time": time_key.replace("-", ":"),
        "label": f"{date_key} {time_key.replace('-', ':')}",
        "generated_at": briefing.get("generated_at", ""),
        "source_total": briefing.get("source_total", 0),
        "method": briefing.get("method", ""),
        "fallback_used": briefing.get("fallback_used", False),
        "top_keywords": hot_keywords[:5],
        "integrated_titles": integrated_titles,
        "path_json": f"archive/{date_key}/{time_key}.json",
        "path_md": f"archive/{date_key}/{time_key}.md",
    }


def update_archive_index(briefing: dict, output_dir: str = "docs/archive") -> None:
    _, _, index_path, date_key, time_key = _archive_paths(briefing, output_dir)
    index_path.parent.mkdir(parents=True, exist_ok=True)

    index_data = _load_archive_index(index_path)
    entry = _archive_index_entry(briefing, date_key, time_key)
    archives = [item for item in index_data.get("archives", []) if item.get("id") != entry["id"]]
    archives.append(entry)
    archives.sort(key=lambda item: item.get("generated_at") or item.get("label", ""), reverse=True)

    index_data = {
        "updated_at": datetime.now(KST).isoformat(),
        "archives": archives,
    }
    index_path.write_text(json.dumps(index_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  ✓ 아카이브 인덱스 갱신: {index_path}")


def write_briefing_archive(briefing: dict, output_dir: str = "docs/archive") -> None:
    output_path, json_path, _, date_key, time_key = _archive_paths(briefing, output_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# {date_key} {time_key.replace('-', ':')} RSS 트렌드 브리핑",
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
    json_path.write_text(json.dumps(briefing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    update_archive_index(briefing, output_dir=output_dir)
    print(f"  ✓ 브리핑 아카이브 갱신: {output_path}")
    print(f"  ✓ 브리핑 JSON 아카이브 갱신: {json_path}")
