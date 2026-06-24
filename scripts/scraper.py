from __future__ import annotations

import argparse
import json
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from archive_writer import write_daily_archive
from rss_collector import collect_feed
from scorer import score_items

KST = ZoneInfo("Asia/Seoul")
ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config.json"
DATA_PATH = ROOT_DIR / "docs" / "data.json"
ARCHIVE_DIR = ROOT_DIR / "docs" / "archive"
MAX_ARCHIVE_ITEMS = 200


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RSS 트렌드 브리핑 수집기")
    parser.add_argument(
        "--group",
        required=True,
        help="수집할 group. 예: news 또는 tech_blog,ai_data",
    )
    return parser.parse_args()


def now_kst_iso() -> str:
    return datetime.now(KST).isoformat()


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def load_data(path: Path = DATA_PATH) -> dict:
    if not path.exists():
        return {"updated_at": "", "total_items": 0, "items": []}

    try:
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        if not isinstance(data.get("items"), list):
            data["items"] = []
        data.setdefault("updated_at", "")
        data["total_items"] = len(data["items"])
        return data
    except Exception as exc:
        print(f"  ! 기존 data.json을 읽지 못했습니다. 새 파일로 재생성합니다: {exc}")
        return {"updated_at": "", "total_items": 0, "items": []}


def save_data(data: dict, path: Path = DATA_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
        fp.write("\n")


def normalize_groups(raw_groups: str) -> set[str]:
    return {group.strip() for group in raw_groups.split(",") if group.strip()}


def select_feeds(config: dict, groups: set[str]) -> list[dict]:
    feeds = []
    for feed in config.get("feeds", []):
        if not feed.get("enabled", False):
            continue
        if feed.get("type") != "rss":
            continue
        if feed.get("group") not in groups:
            continue
        feeds.append(feed)
    return feeds


def sort_datetime_value(value: str) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=KST)
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=KST)
        return dt.astimezone(KST)
    except Exception:
        pass
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=KST)
        return dt.astimezone(KST)
    except Exception:
        return datetime.min.replace(tzinfo=KST)


def item_sort_key(item: dict) -> datetime:
    return sort_datetime_value(item.get("published_at") or item.get("fetched_at") or "")


def dedupe_items(items: list[dict]) -> list[dict]:
    deduped: dict[str, dict] = {}
    for item in sorted(items, key=item_sort_key, reverse=True):
        item_id = item.get("id")
        if item_id and item_id not in deduped:
            deduped[item_id] = item
    return list(deduped.values())


def collect_all(feeds: list[dict]) -> list[dict]:
    collected: list[dict] = []
    for feed in feeds:
        collected.extend(collect_feed(feed))
    return dedupe_items(collected)


def main() -> int:
    args = parse_args()
    groups = normalize_groups(args.group)
    if not groups:
        print("수집할 group이 비어 있습니다.")
        return 2

    print("=" * 60)
    print(f"RSS 트렌드 브리핑 수집 시작: {', '.join(sorted(groups))}")
    print("=" * 60)

    config = load_config()
    feeds = select_feeds(config, groups)
    print(f"[1/4] 대상 피드: {len(feeds)}개")
    if not feeds:
        print("수집 대상 피드가 없습니다. config.json과 --group 값을 확인하세요.")
        return 1

    print("[2/4] RSS 수집")
    collected_items = collect_all(feeds)
    print(f"  - 총 수집 항목: {len(collected_items)}건")

    if not collected_items:
        print("수집된 항목이 없습니다. data.json을 변경하지 않습니다.")
        return 0

    print("[3/4] 신규 항목 판정")
    existing_data = load_data()
    existing_items = existing_data.get("items", [])
    existing_ids = {item.get("id") for item in existing_items if item.get("id")}
    new_items = [item for item in collected_items if item.get("id") not in existing_ids]

    if not new_items:
        print("✅ 신규 항목 없음. data.json을 변경하지 않습니다.")
        return 0

    print(f"  - 신규 항목: {len(new_items)}건")
    scored_new_items = score_items(new_items)
    merged_items = dedupe_items(scored_new_items + existing_items)
    merged_items = sorted(merged_items, key=item_sort_key, reverse=True)[:MAX_ARCHIVE_ITEMS]

    output_data = {
        "updated_at": now_kst_iso(),
        "total_items": len(merged_items),
        "items": merged_items,
    }

    print("[4/4] data.json 및 일자별 아카이브 저장")
    save_data(output_data)
    write_daily_archive(merged_items, output_dir=str(ARCHIVE_DIR))
    print(f"  ✓ data.json 갱신: {DATA_PATH}")
    print(f"완료: 최신 {len(merged_items)}건 유지")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
