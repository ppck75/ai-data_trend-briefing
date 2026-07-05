from __future__ import annotations

import json
import os
import re
import signal
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

KST = ZoneInfo("Asia/Seoul")
GEMINI_MODEL = "gemini-3.1-flash-lite"
GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "45"))
GROUP_ORDER = ("news", "tech_blog", "ai_data")

GROUP_KEYWORDS = {
    "news": [
        "AI",
        "생성형 AI",
        "광고",
        "마케팅",
        "커머스",
        "이커머스",
        "플랫폼",
        "소비자",
        "Z세대",
        "숏폼",
        "릴스",
        "틱톡",
        "유튜브",
        "브랜드",
        "개인화",
        "추천",
        "알고리즘",
        "데이터",
        "검색",
        "콘텐츠",
        "크리에이터",
        "구독",
        "리테일",
    ],
    "tech_blog": [
        "UX",
        "UI",
        "사용자 경험",
        "추천",
        "검색",
        "데이터",
        "실험",
        "A/B test",
        "개인화",
        "랭킹",
        "피드",
        "플랫폼",
        "제품",
        "프로덕트",
        "커머스",
        "결제",
        "온보딩",
        "전환율",
        "리텐션",
        "로그",
        "분석",
        "머신러닝",
        "AI",
        "백엔드",
        "성능",
        "자동화",
    ],
    "ai_data": [
        "LLM",
        "RAG",
        "agent",
        "agents",
        "multimodal",
        "embedding",
        "benchmark",
        "model",
        "dataset",
        "open source",
        "fine-tuning",
        "API",
        "Claude",
        "GPT",
        "Gemini",
        "Hugging Face",
        "transformer",
        "retrieval",
        "evaluation",
        "reasoning",
        "automation",
        "recommendation",
        "personalization",
    ],
}

COMMON_KEYWORDS = [
    "AI",
    "데이터",
    "추천",
    "개인화",
    "자동화",
    "알고리즘",
    "플랫폼",
    "콘텐츠",
    "커머스",
    "마케팅",
    "검색",
    "LLM",
    "RAG",
    "agent",
    "multimodal",
]

LOW_SIGNAL_KEYWORDS = [
    "주가",
    "성과급",
    "인사",
    "파업",
    "화재",
    "사고",
    "실적",
    "매출",
]


def score_items(items: list[dict]) -> list[dict]:
    return items


def _text_for_item(item: dict) -> str:
    return f"{item.get('title', '')} {item.get('summary', '')}".strip()


def _contains_keyword(text: str, keyword: str) -> bool:
    if not keyword:
        return False
    if re.search(r"[A-Za-z]", keyword):
        return keyword.lower() in text.lower()
    return keyword in text


def extract_item_keywords(item: dict, group: str | None = None, limit: int = 5) -> list[str]:
    text = _text_for_item(item)
    candidates = []
    if group in GROUP_KEYWORDS:
        candidates.extend(GROUP_KEYWORDS[group])
    candidates.extend(COMMON_KEYWORDS)

    found: list[str] = []
    for keyword in candidates:
        if keyword not in found and _contains_keyword(text, keyword):
            found.append(keyword)
        if len(found) >= limit:
            break
    return found


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=KST)
        return dt.astimezone(KST)
    except Exception:
        return None


def recency_score(item: dict) -> int:
    dt = _parse_datetime(item.get("published_at") or item.get("fetched_at") or "")
    if dt is None:
        return 3

    age_days = (datetime.now(KST) - dt).total_seconds() / 86400
    if age_days <= 1:
        return 15
    if age_days <= 3:
        return 10
    if age_days <= 7:
        return 5
    return 0


def _keyword_score(item: dict, group: str) -> int:
    text = _text_for_item(item)
    group_hits = sum(1 for keyword in GROUP_KEYWORDS.get(group, []) if _contains_keyword(text, keyword))
    common_hits = sum(1 for keyword in COMMON_KEYWORDS if _contains_keyword(text, keyword))
    return min(35, group_hits * 5 + common_hits * 3)


def _low_signal_penalty(item: dict) -> int:
    text = _text_for_item(item)
    penalty = sum(1 for keyword in LOW_SIGNAL_KEYWORDS if keyword in text) * 4
    return min(16, penalty)


def fallback_category_score(item: dict, group: str) -> int:
    base_score = float(item.get("importance_weight", 0.7) or 0.7) * 20
    keyword_score = _keyword_score(item, group)
    recency = recency_score(item)
    source_bonus = 8 if group == "ai_data" and item.get("source") in {"Anthropic", "Hugging Face Blog"} else 0
    score = base_score + keyword_score + recency + source_bonus - _low_signal_penalty(item)
    return max(0, min(100, round(score)))


def fallback_category_reason(item: dict, keywords: list[str], group: str) -> str:
    if keywords:
        joined = ", ".join(keywords[:3])
        return f"{joined} 관련 신호가 있어 {group} 관점의 트렌드 후보로 볼 수 있습니다."
    return "최근 수집 항목 중 출처 가중치와 최신성을 기준으로 선별되었습니다."


def fallback_planning_insight(item: dict, keywords: list[str]) -> str:
    if keywords:
        joined = ", ".join(keywords[:3])
        return f"이 항목은 {joined} 흐름과 연결되어 콘텐츠 기획 주제로 추가 확인할 가치가 있습니다."
    return "콘텐츠 전략가 관점에서 시장 변화 신호인지 후속 확인할 필요가 있습니다."


def build_category_entry(item: dict, rank: int, group: str, score: int | None = None) -> dict:
    keywords = extract_item_keywords(item, group=group)
    category_score = score if score is not None else fallback_category_score(item, group)
    return {
        "rank": rank,
        "id": item.get("id", ""),
        "title": item.get("title", ""),
        "source": item.get("source", ""),
        "group": item.get("group", group),
        "category": item.get("category", ""),
        "url": item.get("url", ""),
        "published_at": item.get("published_at", ""),
        "summary": item.get("summary", ""),
        "category_score": category_score,
        "score_reason": fallback_category_reason(item, keywords, group),
        "keywords": keywords,
        "planning_insight": fallback_planning_insight(item, keywords),
    }


def fallback_category_top5(items: list[dict]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {group: [] for group in GROUP_ORDER}
    grouped = {group: [] for group in GROUP_ORDER}
    for item in items:
        group = item.get("group")
        if group in grouped:
            grouped[group].append(item)

    for group, group_items in grouped.items():
        scored = sorted(
            group_items,
            key=lambda item: (fallback_category_score(item, group), item.get("published_at") or item.get("fetched_at") or ""),
            reverse=True,
        )
        result[group] = [build_category_entry(item, index + 1, group) for index, item in enumerate(scored[:5])]
    return result


def integrated_scores(candidate: dict) -> dict[str, int]:
    keywords = set(candidate.get("keywords") or [])
    group = candidate.get("group", "")
    text = f"{candidate.get('title', '')} {candidate.get('summary', '')}"

    content_strategy = 10 + min(15, len(keywords & {"콘텐츠", "마케팅", "브랜드", "UX", "제품", "프로덕트", "커머스"}) * 4)
    trend_signal = 8 + recency_score(candidate) + min(7, len(keywords & {"플랫폼", "소비자", "검색", "추천", "AI", "데이터"}) * 2)
    ai_data = 7 + min(18, len(keywords & {"AI", "데이터", "추천", "개인화", "자동화", "알고리즘", "LLM", "RAG", "agent", "multimodal"}) * 4)
    market_consumer = 8 + min(17, len(keywords & {"소비자", "커머스", "마케팅", "브랜드", "플랫폼", "콘텐츠", "리테일"}) * 4)

    if group == "ai_data":
        ai_data += 5
    if group == "tech_blog":
        content_strategy += 4
    if any(keyword in text for keyword in LOW_SIGNAL_KEYWORDS):
        trend_signal -= 4

    return {
        "content_strategy": max(0, min(25, content_strategy)),
        "trend_signal_timeliness": max(0, min(25, trend_signal)),
        "ai_data_relevance": max(0, min(25, ai_data)),
        "market_consumer_impact": max(0, min(25, market_consumer)),
    }


def _dedupe_candidates(candidates: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped = []
    for candidate in candidates:
        key = re.sub(r"\W+", "", candidate.get("title", "").lower())[:40]
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def fallback_integrated_top5(category_top5: dict[str, list[dict]]) -> tuple[list[dict], list[str]]:
    candidates = _dedupe_candidates([item for group in GROUP_ORDER for item in category_top5.get(group, [])])
    enriched = []
    for candidate in candidates:
        criteria = integrated_scores(candidate)
        integrated_score = sum(criteria.values())
        keywords = candidate.get("keywords") or extract_item_keywords(candidate, candidate.get("group"))
        enriched.append(
            {
                **candidate,
                "integrated_score": integrated_score,
                "criteria_scores": criteria,
                "applied_criteria": _applied_criteria(criteria),
                "keywords": keywords,
                "one_line_summary": _one_line_summary(candidate),
                "importance_reason": _importance_reason(candidate, keywords),
                "planning_insight": fallback_planning_insight(candidate, keywords),
            }
        )

    sorted_items = sorted(enriched, key=lambda item: item["integrated_score"], reverse=True)
    selected = sorted_items[:5]
    selected_groups = {item.get("group") for item in selected}
    if len(selected_groups) < 2 and len(sorted_items) > 5:
        for item in sorted_items[5:]:
            if item.get("group") not in selected_groups:
                selected[-1] = item
                break
    selected = sorted(selected, key=lambda item: item["integrated_score"], reverse=True)
    for index, item in enumerate(selected, start=1):
        item["rank"] = index

    return selected, fallback_overall_summary(selected)


def _applied_criteria(criteria: dict[str, int]) -> list[str]:
    labels = {
        "content_strategy": "콘텐츠 전략 활용성",
        "trend_signal_timeliness": "트렌드 신호성·시의성",
        "ai_data_relevance": "AI·데이터 관련성",
        "market_consumer_impact": "시장·소비자 영향력",
    }
    return [labels[key] for key, score in criteria.items() if score >= 18]


def _one_line_summary(item: dict) -> str:
    summary = item.get("summary") or ""
    if summary:
        return summary[:120].rstrip() + ("…" if len(summary) > 120 else "")
    return item.get("title", "")


def _importance_reason(item: dict, keywords: list[str]) -> str:
    if keywords:
        return f"{', '.join(keywords[:3])} 키워드를 중심으로 오늘의 콘텐츠·서비스 전략 흐름과 연결됩니다."
    return "오늘 수집된 항목 중 출처 가중치와 최신성을 기준으로 대표성이 있습니다."


def fallback_overall_summary(integrated_top5: list[dict]) -> list[str]:
    keyword_counts: dict[str, int] = {}
    groups = {item.get("group") for item in integrated_top5}
    for item in integrated_top5:
        for keyword in item.get("keywords", []):
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
    top_keywords = ", ".join(keyword for keyword, _ in sorted(keyword_counts.items(), key=lambda pair: pair[1], reverse=True)[:5])
    return [
        f"오늘 선별된 주요 흐름은 {top_keywords or 'AI·데이터·플랫폼'} 키워드를 중심으로 나타났습니다.",
        f"통합 Top 5에는 {', '.join(sorted(group for group in groups if group))} 그룹의 항목이 반영되었습니다.",
        "콘텐츠 전략 관점에서는 반복 키워드와 원문을 함께 확인해 후속 리서치 주제로 확장하는 것이 좋습니다.",
    ]


def load_gemini_client():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY가 없으면 규칙 기반 fallback 평가를 사용합니다.")
        return None
    try:
        from google import genai

        return genai.Client(api_key=api_key)
    except Exception as exc:
        print(f"Gemini 클라이언트 초기화 실패. fallback 평가를 사용합니다: {exc}")
        return None


def parse_json_response(text: str) -> dict | None:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.I).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or start > end:
        return None
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None


class GeminiTimeoutError(TimeoutError):
    pass


@contextmanager
def gemini_timeout(seconds: int):
    if seconds <= 0 or not hasattr(signal, "SIGALRM"):
        yield
        return

    def _handle_timeout(signum, frame):
        raise GeminiTimeoutError(f"Gemini 호출 제한시간 {seconds}초 초과")

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _handle_timeout)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)


def call_gemini_json(client, prompt: str) -> dict | None:
    if client is None:
        return None
    try:
        with gemini_timeout(GEMINI_TIMEOUT_SECONDS):
            response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return parse_json_response(getattr(response, "text", "") or "")
    except Exception as exc:
        print(f"Gemini 평가 호출 실패. fallback 평가를 사용합니다: {exc}")
        return None
