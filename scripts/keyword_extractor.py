from __future__ import annotations

import re
from collections import Counter, defaultdict

PROJECT_KEYWORDS = [
    "AI",
    "생성형 AI",
    "LLM",
    "RAG",
    "agent",
    "agents",
    "multimodal",
    "데이터",
    "추천",
    "개인화",
    "자동화",
    "알고리즘",
    "검색",
    "콘텐츠",
    "마케팅",
    "광고",
    "커머스",
    "이커머스",
    "플랫폼",
    "소비자",
    "브랜드",
    "크리에이터",
    "숏폼",
    "유튜브",
    "틱톡",
    "UX",
    "UI",
    "실험",
    "분석",
    "API",
    "Claude",
    "GPT",
    "Gemini",
    "Hugging Face",
    "dataset",
    "model",
    "open source",
    "embedding",
    "evaluation",
    "reasoning",
]

STOPWORDS = {
    "그리고",
    "하지만",
    "있는",
    "없는",
    "위한",
    "통해",
    "으로",
    "에서",
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "into",
    "about",
    "using",
}


def _text_for_item(item: dict) -> str:
    return f"{item.get('title', '')} {item.get('summary', '')}"


def _contains_keyword(text: str, keyword: str) -> bool:
    if re.search(r"[A-Za-z]", keyword):
        return keyword.lower() in text.lower()
    return keyword in text


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+.#-]{2,}|[가-힣]{2,}", text)
    return [token for token in tokens if token.lower() not in STOPWORDS]


def extract_hot_keywords(items: list[dict], limit: int = 5) -> list[dict]:
    counts: Counter[str] = Counter()
    groups: dict[str, set[str]] = defaultdict(set)
    sources: dict[str, set[str]] = defaultdict(set)

    for item in items:
        text = _text_for_item(item)
        matched = set()
        for keyword in PROJECT_KEYWORDS:
            if _contains_keyword(text, keyword):
                matched.add(keyword)
        for token in _tokenize(text):
            if token in PROJECT_KEYWORDS or token.upper() in {"AI", "LLM", "RAG", "API", "UX", "UI"}:
                matched.add(token)

        for keyword in matched:
            counts[keyword] += 1
            if item.get("group"):
                groups[keyword].add(item["group"])
            if item.get("source"):
                sources[keyword].add(item["source"])

    return [
        {
            "keyword": keyword,
            "count": count,
            "groups": sorted(groups[keyword]),
            "sources": sorted(sources[keyword])[:5],
        }
        for keyword, count in counts.most_common(limit)
    ]
