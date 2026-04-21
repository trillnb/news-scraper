import argparse
import json
import requests
from bs4 import BeautifulSoup
from parser import process_articles
from pathlib import Path

HN_URL = "https://news.ycombinator.com/"
HN_PAGE_LIMIT = 30
CONFIG_FILE = Path("config.json")


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Error: config.json is not valid JSON: {e}")
    except OSError as e:
        raise SystemExit(f"Error: could not read config.json: {e}")


def _positive_int(value: str) -> int:
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {n}")
    return n


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scrape top stories from Hacker News.")
    p.add_argument("--limit", type=_positive_int, default=None, metavar="N",
                   help="Number of articles to fetch (overrides config)")
    p.add_argument("--min-score", type=int, default=None, metavar="N",
                   help="Minimum score threshold (overrides config)")
    p.add_argument("--output", default=None, metavar="FILE",
                   help="Output JSON filename (overrides config)")
    return p.parse_args()


def fetch_articles(limit: int = 30) -> list[dict]:
    if limit > HN_PAGE_LIMIT:
        print(f"Warning: HN front page only shows {HN_PAGE_LIMIT} articles; "
              f"capping --limit at {HN_PAGE_LIMIT}.")
        limit = HN_PAGE_LIMIT

    headers = {"User-Agent": "Mozilla/5.0 (compatible; HN-Scraper/1.0)"}
    try:
        response = requests.get(HN_URL, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise SystemExit("Error: could not reach news.ycombinator.com. Check your connection.")
    except requests.exceptions.Timeout:
        raise SystemExit("Error: request timed out after 10 seconds.")
    except requests.exceptions.HTTPError as e:
        raise SystemExit(f"Error: server returned {e.response.status_code}.")

    soup = BeautifulSoup(response.text, "html.parser")
    articles = []

    for row in soup.select("tr.athing")[:limit]:
        item_id = row.get("id")

        title_tag = row.select_one("span.titleline > a")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        link = title_tag.get("href", "")
        if link.startswith("item?"):
            link = HN_URL + link

        subtext = row.find_next_sibling("tr")
        if not subtext:
            continue

        score_tag = subtext.select_one(f"span#score_{item_id}")
        score = int(score_tag.get_text().split()[0]) if score_tag else 0

        author_tag = subtext.select_one("a.hnuser")
        author = author_tag.get_text(strip=True) if author_tag else "unknown"

        age_tag = subtext.select_one("span.age")
        posted_at = age_tag.get("title", "") if age_tag else ""

        comments_tag = subtext.select("a")[-1] if subtext.select("a") else None
        comments = 0
        if comments_tag and "comment" in comments_tag.get_text():
            try:
                comments = int(comments_tag.get_text().split()[0])
            except ValueError:
                comments = 0

        articles.append({
            "title": title,
            "link": link,
            "score": score,
            "comments": comments,
            "author": author,
            "posted_at": posted_at,
        })

    return articles


def run(limit: int, min_score: int, output: str) -> int:
    """Fetch, filter, and save articles. Returns the number of saved articles."""
    articles = fetch_articles(limit=limit)
    print(f"Fetched {len(articles)} articles.")
    process_articles(articles, score_threshold=min_score, output=output)
    return sum(1 for a in articles if a["score"] >= min_score)


if __name__ == "__main__":
    args = parse_args()
    cfg = load_config()

    limit    = args.limit     if args.limit     is not None else cfg.get("limit", 30)
    min_score = args.min_score if args.min_score is not None else cfg.get("min_score", 100)
    output   = args.output    if args.output    is not None else cfg.get("output_file", "data.json")

    print(f"Scraping Hacker News (limit={limit}, min-score={min_score}, output={output})...")
    run(limit, min_score, output)
