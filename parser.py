import csv
import json
import shutil
from pathlib import Path


def filter_by_score(articles: list[dict], threshold: int) -> list[dict]:
    return [a for a in articles if a["score"] >= threshold]


def save_json(articles: list[dict], path: Path) -> None:
    if path.exists():
        backup = path.with_name(path.stem + "_prev" + path.suffix)
        try:
            shutil.copy2(path, backup)
        except OSError as e:
            print(f"Warning: could not create backup {backup}: {e}")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
    except OSError as e:
        raise SystemExit(f"Error: could not write {path}: {e}")
    print(f"Saved {len(articles)} articles to {path}")


def save_csv(articles: list[dict], path: Path) -> None:
    if not articles:
        return
    fieldnames = ["title", "link", "score", "comments", "author", "posted_at"]
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
            writer.writeheader()
            writer.writerows(articles)
    except OSError as e:
        raise SystemExit(f"Error: could not write {path}: {e}")
    print(f"Saved {len(articles)} articles to {path}")


def print_top5(articles: list[dict]) -> None:
    top5 = sorted(articles, key=lambda a: a["score"], reverse=True)[:5]
    if not top5:
        print("No articles to display.")
        return

    width = 72
    border = "─" * width

    print(f"\n{'':^4}┌{border}┐")
    print(f"{'':^4}│{'  TOP-5 HACKER NEWS':^{width}}│")
    print(f"{'':^4}├{border}┤")

    for i, article in enumerate(top5, start=1):
        title = article["title"]
        if len(title) > width - 4:
            title = title[: width - 7] + "..."

        score_line = (
            f"  ▲ {article['score']} pts"
            f"  💬 {article['comments']} comments"
            f"  👤 {article['author']}"
        )
        link = article["link"]
        if len(link) > width - 4:
            link = link[: width - 7] + "..."

        print(f"{'':^4}│  {i}. {title:<{width - 5}}│")
        print(f"{'':^4}│{score_line:<{width + 2}}│")
        print(f"{'':^4}│  {link:<{width - 2}}│")

        if i < len(top5):
            print(f"{'':^4}├{'─' * width}┤")

    print(f"{'':^4}└{border}┘\n")


def process_articles(
    articles: list[dict],
    score_threshold: int = 100,
    output: str = "data.json",
) -> None:
    filtered = filter_by_score(articles, score_threshold)
    print(f"Articles with score >= {score_threshold}: {len(filtered)}")

    json_path = Path(output)
    csv_path = json_path.with_suffix(".csv")

    save_json(filtered, json_path)
    save_csv(filtered, csv_path)
    print_top5(filtered)
