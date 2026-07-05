from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from archive_writer import write_briefing_archive
from keyword_extractor import extract_hot_keywords
from scorer import (
    GEMINI_MODEL,
    GROUP_ORDER,
    build_category_entry,
    call_gemini_json,
    fallback_category_score,
    fallback_category_top5,
    fallback_integrated_top5,
    integrated_scores,
    load_gemini_client,
)

KST = ZoneInfo("Asia/Seoul")
ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT_DIR / "docs" / "data.json"
DEFAULT_OUTPUT = ROOT_DIR / "docs" / "briefing.json"
DEFAULT_ARCHIVE_DIR = ROOT_DIR / "docs" / "archive"
GEMINI_GROUP_CANDIDATE_LIMIT = 60


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RSS 트렌드 브리핑 생성기")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="입력 data.json 경로")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="출력 briefing.json 경로")
    parser.add_argument(
        "--skip-archive",
        action="store_true",
        help="docs/briefing.json만 갱신하고 날짜별 아카이브는 생성하지 않습니다.",
    )
    parser.add_argument(
        "--fallback-only",
        action="store_true",
        help="Gemini 호출 없이 규칙 기반 fallback으로 브리핑을 생성합니다.",
    )
    return parser.parse_args()


def now_kst() -> datetime:
    return datetime.now(KST)


def load_data(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data.get("items"), list):
        data["items"] = []
    return data


def save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
        fp.write("\n")


def compact_item(item: dict) -> dict:
    summary = item.get("summary", "")
    return {
        "id": item.get("id", ""),
        "source": item.get("source", ""),
        "group": item.get("group", ""),
        "category": item.get("category", ""),
        "title": item.get("title", ""),
        "summary": summary[:350],
        "published_at": item.get("published_at", ""),
        "importance_weight": item.get("importance_weight", 0.7),
    }


def count_by_group(items: list[dict]) -> dict[str, int]:
    return {group: sum(1 for item in items if item.get("group") == group) for group in GROUP_ORDER}


def select_gemini_group_candidates(items: list[dict], group: str, limit: int = GEMINI_GROUP_CANDIDATE_LIMIT) -> list[dict]:
    group_items = [item for item in items if item.get("group") == group]
    return sorted(
        group_items,
        key=lambda item: (
            fallback_category_score(item, group),
            item.get("published_at") or item.get("fetched_at") or "",
        ),
        reverse=True,
    )[:limit]


GROUP_PROMPT_CONFIG = {
    "news": {
        "title": "뉴스성 RSS",
        "criteria": [
            "시장·소비자 변화 신호인가?",
            "플랫폼/광고/커머스/AI와 연결되는가?",
            "여러 매체에서 반복될 가능성이 있는가?",
            "단순 사건이 아니라 트렌드로 확장 가능한가?",
        ],
        "direction": [
            "단순 사건보다 시장 변화 신호에 높은 점수를 주세요.",
            "기업 실적, 주가, 인사, 사건 사고는 트렌드 연결성이 약하면 낮게 평가하세요.",
            "AI, 플랫폼, 커머스, 광고, 소비자 행동과 연결되면 높게 평가하세요.",
            "최근 발행된 항목은 시의성 관점에서 가산하세요.",
        ],
    },
    "tech_blog": {
        "title": "플랫폼·서비스 기술블로그",
        "criteria": [
            "실제 서비스 기획에 적용 가능한가?",
            "UX, 추천, 검색, 데이터 활용 사례가 있는가?",
            "플랫폼 운영 방식이나 제품 전략을 보여주는가?",
            "콘텐츠 전략가가 참고할 만한 구조적 인사이트가 있는가?",
        ],
        "direction": [
            "단순 개발 회고보다 서비스 기획이나 사용자 경험에 연결되는 글을 우선하세요.",
            "추천, 검색, 데이터 분석, UX 개선, 실험 설계 관련 글에 높은 점수를 주세요.",
            "제품 구조나 운영 방식이 보이면 높게 평가하세요.",
            "내부 개발 인프라에만 치우친 글은 낮게 평가하세요.",
        ],
    },
    "ai_data": {
        "title": "AI·데이터 트렌드",
        "criteria": [
            "LLM, RAG, 에이전트, 멀티모달 등 핵심 AI 흐름과 관련 있는가?",
            "콘텐츠 제작·추천·분석 자동화에 연결 가능한가?",
            "모델/API/데이터셋/오픈소스 변화인가?",
            "기획자가 알아야 할 기술 변화인가?",
        ],
        "direction": [
            "기획자가 이해하고 활용할 수 있는 AI 변화에 높은 점수를 주세요.",
            "콘텐츠 제작, 추천, 자동화, 데이터 분석과 연결되는 글을 우선하세요.",
            "LLM, RAG, 멀티모달, 에이전트 흐름과 관련 있으면 높게 평가하세요.",
            "세부 수학이나 모델 구조만 다루고 기획 활용성이 낮으면 낮게 평가하세요.",
        ],
    },
}


def build_category_prompt(group: str, items: list[dict]) -> str:
    config = GROUP_PROMPT_CONFIG[group]
    payload = [compact_item(item) for item in items if item.get("group") == group]
    criteria = "\n".join(f"- {line}" for line in config["criteria"])
    direction = "\n".join(f"- {line}" for line in config["direction"])
    return f"""
당신은 AI·데이터 기반 콘텐츠 전략가입니다.

아래 RSS 항목은 모두 `{group}` group에 속한 {config["title"]} 항목입니다.
아래 평가 기준에 따라 이 group 안에서 Top 5만 선정하세요.

[평가 기준]
{criteria}

[점수화 방향]
{direction}

[출력 규칙]
- `{group}` group에서만 Top 5를 선정하세요.
- 같은 사건이나 유사한 글이 중복되면 가장 정보가 풍부한 항목만 남기세요.
- 반드시 item id를 유지하세요.
- 결과는 설명문이 아니라 JSON만 출력하세요.
- JSON 스키마:
{{
  "category_top5": {{
    "{group}": [
      {{
        "rank": 1,
        "id": "item_id",
        "category_score": 87,
        "score_reason": "선정 이유",
        "keywords": ["AI", "플랫폼"],
        "planning_insight": "콘텐츠 전략 인사이트"
      }}
    ]
  }}
}}

[RSS 항목: {len(payload)}개]
{json.dumps(payload, ensure_ascii=False)}
""".strip()


def build_integrated_prompt(candidates: list[dict]) -> str:
    payload = [
        {
            "id": item.get("id", ""),
            "source": item.get("source", ""),
            "group": item.get("group", ""),
            "category": item.get("category", ""),
            "title": item.get("title", ""),
            "summary": item.get("summary", "")[:500],
            "category_score": item.get("category_score"),
            "score_reason": item.get("score_reason", ""),
            "keywords": item.get("keywords", []),
            "planning_insight": item.get("planning_insight", ""),
        }
        for item in candidates
    ]
    return f"""
당신은 AI·데이터 기반 콘텐츠 전략가입니다.

아래 후보들은 이미 카테고리별로 1차 선별된 RSS 항목입니다.
이 중 오늘의 전체 브리핑을 대표할 통합 Top 5를 선정하세요.

[통합 Top 5 평가 기준: 총 100점]

1. 콘텐츠 전략 활용성 25점
- 이 이슈가 콘텐츠 기획, 캠페인 아이디어, 서비스 기획, 리서치 주제로 확장 가능한가?
- 블로그, 카드뉴스, 리포트, 숏폼, 브랜디드 콘텐츠 등으로 발전시킬 수 있는가?

2. 트렌드 신호성·시의성 25점
- 단순 사건이 아니라 반복되는 흐름이나 변화의 신호인가?
- 최근에 발행되었거나, 현재 시점에서 다시 중요해진 이슈인가?
- 지금 콘텐츠 기획자나 서비스 기획자가 확인해야 할 만큼 시의성이 있는가?
- 앞으로 계속 추적할 만한 키워드와 연결되는가?
- 다른 기사, 기술블로그, AI 업데이트와 연결될 수 있는 흐름인가?

3. AI·데이터 관련성 25점
- AI, 데이터, 추천, 자동화, 알고리즘, 모델, 분석, 개인화와 관련 있는가?
- 콘텐츠 제작·분석·배포 방식이나 기획자의 의사결정 방식에 영향을 줄 수 있는가?

4. 시장·소비자 영향력 25점
- 소비자 행동, 플랫폼 이용 방식, 브랜드 전략, 커머스 흐름에 영향을 줄 수 있는가?
- 마케팅·콘텐츠 환경의 변화를 보여주는가?

[선정 규칙]
- 최종 Top 5는 점수순으로 선정하되, 최소 2개 이상의 group이 포함되게 하세요.
- 같은 사건이나 같은 키워드가 중복되면 가장 정보가 풍부한 항목만 남기세요.
- 단순 기업 실적, 주가, 인사, 사건 사고는 트렌드 신호성이 약하면 제외하세요.
- 제목에 AI가 들어가더라도 실제 AI·데이터 활용성과 연결되지 않으면 높은 점수를 주지 마세요.
- 반대로 기술블로그나 논문 항목이라도 콘텐츠 전략, 제품 기획, 데이터 기반 의사결정과 연결되면 포함하세요.

[출력 규칙]
- 결과는 설명문이 아니라 JSON만 출력하세요.
- 반드시 item id를 유지하세요.
- JSON 스키마:
{{
  "integrated_top5": [
    {{
      "rank": 1,
      "id": "item_id",
      "integrated_score": 92,
      "criteria_scores": {{
        "content_strategy": 23,
        "trend_signal_timeliness": 24,
        "ai_data_relevance": 23,
        "market_consumer_impact": 22
      }},
      "applied_criteria": ["콘텐츠 전략 활용성", "트렌드 신호성·시의성", "AI·데이터 관련성"],
      "keywords": ["AI", "개인화", "콘텐츠 자동화"],
      "one_line_summary": "한 줄 요약",
      "importance_reason": "왜 중요한가",
      "planning_insight": "콘텐츠 전략 인사이트"
    }}
  ],
  "overall_summary": ["오늘 전체 흐름 요약 1", "오늘 전체 흐름 요약 2", "오늘 전체 흐름 요약 3"]
}}

[후보 항목]
{json.dumps(payload, ensure_ascii=False)}
""".strip()


def enrich_category_results(raw: dict, items: list[dict]) -> dict[str, list[dict]] | None:
    if not raw or not isinstance(raw.get("category_top5"), dict):
        return None

    item_by_id = {item.get("id"): item for item in items if item.get("id")}
    fallback = fallback_category_top5(items)
    result: dict[str, list[dict]] = {group: [] for group in GROUP_ORDER}

    for group in GROUP_ORDER:
        seen: set[str] = set()
        raw_items = raw["category_top5"].get(group, [])
        if not isinstance(raw_items, list):
            raw_items = []
        for entry in raw_items:
            item_id = entry.get("id") if isinstance(entry, dict) else None
            if not item_id or item_id in seen or item_id not in item_by_id:
                continue
            item = item_by_id[item_id]
            if item.get("group") != group:
                continue
            enriched = build_category_entry(
                item,
                rank=len(result[group]) + 1,
                group=group,
                score=entry.get("category_score"),
            )
            for key in ("score_reason", "planning_insight"):
                if entry.get(key):
                    enriched[key] = entry[key]
            if isinstance(entry.get("keywords"), list):
                enriched["keywords"] = entry["keywords"][:5]
            result[group].append(enriched)
            seen.add(item_id)
            if len(result[group]) >= 5:
                break

        if len(result[group]) < 5:
            for fallback_item in fallback[group]:
                if fallback_item["id"] in seen:
                    continue
                fallback_item = {**fallback_item, "rank": len(result[group]) + 1}
                result[group].append(fallback_item)
                seen.add(fallback_item["id"])
                if len(result[group]) >= 5:
                    break

    return result


def enrich_category_group_result(raw: dict, group: str, group_items: list[dict]) -> list[dict] | None:
    if not raw or not isinstance(raw.get("category_top5"), dict):
        return None

    raw_items = raw["category_top5"].get(group, [])
    if not isinstance(raw_items, list):
        return None

    item_by_id = {item.get("id"): item for item in group_items if item.get("id")}
    fallback_items = fallback_category_top5(group_items).get(group, [])
    result: list[dict] = []
    seen: set[str] = set()

    for entry in raw_items:
        item_id = entry.get("id") if isinstance(entry, dict) else None
        if not item_id or item_id in seen or item_id not in item_by_id:
            continue
        item = item_by_id[item_id]
        if item.get("group") != group:
            continue
        enriched = build_category_entry(
            item,
            rank=len(result) + 1,
            group=group,
            score=entry.get("category_score"),
        )
        for key in ("score_reason", "planning_insight"):
            if entry.get(key):
                enriched[key] = entry[key]
        if isinstance(entry.get("keywords"), list):
            enriched["keywords"] = entry["keywords"][:5]
        result.append(enriched)
        seen.add(item_id)
        if len(result) >= 5:
            break

    for fallback_item in fallback_items:
        if len(result) >= 5:
            break
        if fallback_item["id"] in seen:
            continue
        result.append({**fallback_item, "rank": len(result) + 1})
        seen.add(fallback_item["id"])

    return result if result else None


def enrich_integrated_results(raw: dict, category_top5: dict[str, list[dict]]) -> tuple[list[dict], list[str]] | None:
    if not raw or not isinstance(raw.get("integrated_top5"), list):
        return None

    candidates = [item for group in GROUP_ORDER for item in category_top5.get(group, [])]
    candidate_by_id = {item.get("id"): item for item in candidates if item.get("id")}
    selected = []
    seen: set[str] = set()

    for entry in raw["integrated_top5"]:
        item_id = entry.get("id") if isinstance(entry, dict) else None
        if not item_id or item_id in seen or item_id not in candidate_by_id:
            continue
        candidate = candidate_by_id[item_id]
        criteria = entry.get("criteria_scores") if isinstance(entry.get("criteria_scores"), dict) else integrated_scores(candidate)
        integrated_score = entry.get("integrated_score")
        if not isinstance(integrated_score, int):
            integrated_score = sum(int(value) for value in criteria.values())
        selected.append(
            {
                **candidate,
                "rank": len(selected) + 1,
                "integrated_score": integrated_score,
                "criteria_scores": criteria,
                "applied_criteria": entry.get("applied_criteria") or [],
                "keywords": entry.get("keywords") or candidate.get("keywords", []),
                "one_line_summary": entry.get("one_line_summary") or candidate.get("summary", "")[:120],
                "importance_reason": entry.get("importance_reason") or candidate.get("score_reason", ""),
                "planning_insight": entry.get("planning_insight") or candidate.get("planning_insight", ""),
            }
        )
        seen.add(item_id)
        if len(selected) >= 5:
            break

    if len(selected) < 5:
        fallback_selected, fallback_summary = fallback_integrated_top5(category_top5)
        for item in fallback_selected:
            if item["id"] in seen:
                continue
            item = {**item, "rank": len(selected) + 1}
            selected.append(item)
            seen.add(item["id"])
            if len(selected) >= 5:
                break
        if not raw.get("overall_summary"):
            return selected, fallback_summary

    groups = {item.get("group") for item in selected}
    if len(groups) < 2:
        fallback_selected, fallback_summary = fallback_integrated_top5(category_top5)
        return fallback_selected, raw.get("overall_summary") or fallback_summary

    return selected, raw.get("overall_summary") or []


def generate_briefing(items: list[dict], use_gemini: bool = True) -> dict:
    generated_at = now_kst()
    client = load_gemini_client() if use_gemini else None
    method = "fallback"
    fallback_used = True
    gemini_call_count = 0
    category_methods: dict[str, str] = {group: "fallback" for group in GROUP_ORDER}

    category_top5 = fallback_category_top5(items)
    category_success_groups: set[str] = set()
    if not use_gemini:
        print("Gemini 호출을 건너뛰고 fallback 평가를 사용합니다.")
    if client is not None:
        print(f"Gemini 카테고리별 평가를 시도합니다. model={GEMINI_MODEL}")
        for group in GROUP_ORDER:
            group_items_all = [item for item in items if item.get("group") == group]
            if not group_items_all:
                continue
            group_items = select_gemini_group_candidates(group_items_all, group)
            print(f"  - {group} Top 5 평가 호출 ({len(group_items)} / {len(group_items_all)}건)")
            gemini_call_count += 1
            category_raw = call_gemini_json(client, build_category_prompt(group, group_items))
            group_result = enrich_category_group_result(category_raw, group, group_items)
            if group_result is None:
                print(f"    fallback 사용: {group}")
                continue
            category_top5[group] = group_result
            category_methods[group] = "gemini"
            category_success_groups.add(group)

    if category_success_groups:
        method = "gemini"
        fallback_used = len(category_success_groups) < len(GROUP_ORDER)

    candidates = [item for group in GROUP_ORDER for item in category_top5.get(group, [])]
    integrated_result = None
    if client is not None and category_success_groups:
        print("  - 통합 Top 5 평가 호출 (15개 후보)")
        gemini_call_count += 1
        integrated_raw = call_gemini_json(client, build_integrated_prompt(candidates))
        integrated_result = enrich_integrated_results(integrated_raw, category_top5)

    if integrated_result is None:
        integrated_top5, overall_summary = fallback_integrated_top5(category_top5)
        method = "fallback" if not category_success_groups else "gemini"
        fallback_used = True
    else:
        integrated_top5, overall_summary = integrated_result

    return {
        "briefing_date": generated_at.date().isoformat(),
        "generated_at": generated_at.isoformat(),
        "source_total": len(items),
        "category_counts": count_by_group(items),
        "category_top5": category_top5,
        "integrated_top5": integrated_top5,
        "hot_keywords": extract_hot_keywords(items),
        "overall_summary": overall_summary,
        "method": method,
        "fallback_used": fallback_used,
        "gemini_call_count": gemini_call_count,
        "category_methods": category_methods,
    }


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    print("=" * 60)
    print("RSS 트렌드 브리핑 생성 시작")
    print("=" * 60)
    data = load_data(input_path)
    items = data.get("items", [])
    if not items:
        print("docs/data.json에 항목이 없습니다. 먼저 RSS 수집을 실행하세요.")
        return 1

    print(f"[1/3] 입력 항목: {len(items)}건")
    briefing = generate_briefing(items, use_gemini=not args.fallback_only)
    print("[2/3] briefing.json 저장")
    save_json(briefing, output_path)
    print(f"  ✓ 브리핑 JSON 갱신: {output_path}")
    if args.skip_archive:
        print("[3/3] Markdown 아카이브 저장 건너뜀 (--skip-archive)")
    else:
        print("[3/3] Markdown 아카이브 저장")
        write_briefing_archive(briefing, output_dir=str(DEFAULT_ARCHIVE_DIR))
    print("완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
