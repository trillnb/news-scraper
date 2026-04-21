import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

DATA_FILE = Path("data.json")
PREV_DATA_FILE = DATA_FILE.with_name("data_prev.json")
BAR_CHAR = "█"
BAR_MAX_WIDTH = 40
SECTION_WIDTH = 60


# ── helpers ───────────────────────────────────────────────────────────────────

def load_data(path: Path) -> list[dict]:
    if not path.exists():
        sys.exit(f"Error: {path} not found. Run scraper.py first.")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not data:
        sys.exit(f"Error: {path} is empty.")
    return data


def load_prev_data(path: Path) -> list[dict] | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data or None


def _parse_time(posted_at: str) -> datetime | None:
    parts = posted_at.strip().split()
    if not parts:
        return None
    try:
        return datetime.fromisoformat(parts[0])
    except ValueError:
        return None


def section(title: str) -> None:
    inner = SECTION_WIDTH - 2
    if len(title) > inner - 2:
        title = title[: inner - 5] + "..."
    print(f"\n┌{'─' * inner}┐")
    print(f"│  {title:<{inner - 2}}│")
    print(f"└{'─' * inner}┘")


def _truncate(text: str, max_len: int = 52) -> str:
    return text if len(text) <= max_len else text[:max_len - 3] + "..."


# ── stats ─────────────────────────────────────────────────────────────────────

def avg_score(articles: list[dict]) -> None:
    section("Average score")
    scores = [a["score"] for a in articles]
    avg = sum(scores) / len(scores)
    print(f"  Articles analysed : {len(articles)}")
    print(f"  Average score     : {avg:.1f}")
    print(f"  Highest           : {max(scores)}")
    print(f"  Lowest            : {min(scores)}")


def top_author(articles: list[dict]) -> None:
    section("Most active author in this dataset")
    counts = Counter(a["author"] for a in articles)
    author, n = counts.most_common(1)[0]
    print(f"  {author}  —  {n} article{'s' if n > 1 else ''}")
    runners = [(name, cnt) for name, cnt in counts.most_common(4)[1:] if name != "unknown"]
    if runners:
        print("  Runner-ups:")
        for name, cnt in runners:
            print(f"    {name}  —  {cnt}")


def peak_hour(articles: list[dict]) -> None:
    section("Peak posting hour (UTC)")
    times = [_parse_time(a.get("posted_at", "")) for a in articles]
    times = [t for t in times if t is not None]
    if not times:
        print("  No timestamp data available.")
        print("  Re-run scraper.py to collect posted_at field.")
        return

    hour_counts: Counter = Counter(t.hour for t in times)
    peak, count = hour_counts.most_common(1)[0]
    print(f"  Peak hour  : {peak:02d}:00 – {peak:02d}:59 UTC  ({count} articles)")
    print()
    max_count = max(hour_counts.values())
    for h in sorted(hour_counts):
        bar_len = round(hour_counts[h] / max_count * 20)
        bar = BAR_CHAR * bar_len
        print(f"  {h:02d}h  {bar:<20}  {hour_counts[h]}")


def score_histogram(articles: list[dict]) -> None:
    section("Score distribution (histogram)")
    scores = [a["score"] for a in articles]
    lo, hi = min(scores), max(scores)

    if lo == hi:
        print(f"  All {len(scores)} articles have the same score: {lo}")
        print(f"\n  {lo}  {BAR_CHAR * BAR_MAX_WIDTH}  {len(scores)}")
        return

    raw_step = (hi - lo) / 8
    magnitude = 10 ** (len(str(int(raw_step))) - 1) if int(raw_step) > 0 else 1
    step = max(1, round(raw_step / magnitude) * magnitude)

    bucket_start = (lo // step) * step
    buckets: dict[int, int] = {}
    s = bucket_start
    while s <= hi:
        buckets[s] = 0
        s += step

    for score in scores:
        key = (score // step) * step
        if key not in buckets:
            buckets[key] = 0
        buckets[key] += 1

    max_count = max(buckets.values()) or 1
    label_w = len(str(max(buckets) + step - 1))

    print(f"  Bucket size: {step} pts\n")
    for start in sorted(buckets):
        end = start + step - 1
        count = buckets[start]
        bar_len = round(count / max_count * BAR_MAX_WIDTH)
        bar = BAR_CHAR * bar_len
        label = f"{start:>{label_w}}–{end:<{label_w}}"
        print(f"  {label}  {bar:<{BAR_MAX_WIDTH}}  {count}")


def compare_runs(current: list[dict], previous: list[dict]) -> None:
    section("Changes since last run")

    curr_map = {a["link"]: a for a in current}
    prev_map = {a["link"]: a for a in previous}

    new_articles = [a for link, a in curr_map.items() if link not in prev_map]
    gone_articles = [a for link, a in prev_map.items() if link not in curr_map]

    score_changes: list[tuple[dict, int]] = []
    for link, curr in curr_map.items():
        if link in prev_map:
            delta = curr["score"] - prev_map[link]["score"]
            if delta != 0:
                score_changes.append((curr, delta))
    score_changes.sort(key=lambda x: abs(x[1]), reverse=True)

    if not new_articles and not gone_articles and not score_changes:
        print("  No changes detected since last run.")
        return

    if new_articles:
        print(f"  + {len(new_articles)} new article{'s' if len(new_articles) > 1 else ''}:")
        for a in new_articles:
            print(f"    · {_truncate(a['title'])}  (▲{a['score']})")

    rose = [(a, d) for a, d in score_changes if d > 0]
    fell = [(a, d) for a, d in score_changes if d < 0]

    if rose:
        print(f"\n  ↑ Score grew ({len(rose)}):")
        for a, delta in rose:
            prev_score = a["score"] - delta
            print(f"    {_truncate(a['title'])}  {prev_score} → {a['score']}  (+{delta})")

    if fell:
        print(f"\n  ↓ Score dropped ({len(fell)}):")
        for a, delta in fell:
            prev_score = a["score"] - delta
            print(f"    {_truncate(a['title'])}  {prev_score} → {a['score']}  ({delta})")

    if gone_articles:
        print(f"\n  - {len(gone_articles)} article{'s' if len(gone_articles) > 1 else ''} left the top:")
        for a in gone_articles:
            print(f"    · {_truncate(a['title'])}")


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    articles = load_data(DATA_FILE)
    print(f"\nAnalysing {DATA_FILE}  ({len(articles)} articles)")

    avg_score(articles)
    top_author(articles)
    peak_hour(articles)
    score_histogram(articles)

    previous = load_prev_data(PREV_DATA_FILE)
    if previous is not None:
        compare_runs(articles, previous)
    else:
        section("Changes since last run")
        print(f"  No previous snapshot found ({PREV_DATA_FILE}).")
        print("  Run scraper again to enable comparison.")

    print()


if __name__ == "__main__":
    main()
