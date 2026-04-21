import argparse
import json
import sys
from pathlib import Path


def _load_config() -> dict:
    from scraper import load_config
    return load_config()


def cmd_scrape(args: argparse.Namespace) -> None:
    from scraper import fetch_articles, load_config
    from parser import process_articles

    cfg = load_config()
    limit     = args.limit     if args.limit     is not None else cfg.get("limit", 30)
    min_score = args.min_score if args.min_score is not None else cfg.get("min_score", 100)
    output    = args.output    if args.output    is not None else cfg.get("output_file", "data.json")

    print(f"Scraping Hacker News (limit={limit}, min-score={min_score}, output={output})...")
    articles = fetch_articles(limit=limit)
    print(f"Fetched {len(articles)} articles.")
    process_articles(articles, score_threshold=min_score, output=output)


def cmd_analyze(_args: argparse.Namespace) -> None:
    import analyze
    analyze.main()


def cmd_watch(args: argparse.Namespace) -> None:
    from scheduler import watch
    cfg = _load_config()
    watch(interval_minutes=args.interval, config=cfg)


def cmd_config(_args: argparse.Namespace) -> None:
    cfg = _load_config()
    config_path = Path("config.json")

    print(f"\nConfig file: {config_path.resolve()}\n")
    print(json.dumps(cfg, indent=2, ensure_ascii=False))

    print("\nActive defaults:")
    print(f"  limit       : {cfg.get('limit', 30)}")
    print(f"  min_score   : {cfg.get('min_score', 100)}")
    print(f"  output_file : {cfg.get('output_file', 'data.json')}")
    print(f"  sources     : {', '.join(cfg.get('sources', ['hackernews']))}\n")


def _positive_int(value: str) -> int:
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {n}")
    return n


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Hacker News CLI scraper",
    )
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    # scrape
    p_scrape = sub.add_parser("scrape", help="Fetch articles from Hacker News")
    p_scrape.add_argument("--limit", type=_positive_int, default=None, metavar="N",
                          help="Number of articles to fetch (overrides config)")
    p_scrape.add_argument("--min-score", type=int, default=None, metavar="N",
                          help="Minimum score threshold (overrides config)")
    p_scrape.add_argument("--output", default=None, metavar="FILE",
                          help="Output JSON filename (overrides config)")

    # analyze
    sub.add_parser("analyze", help="Analyse data.json and show stats")

    # watch
    p_watch = sub.add_parser("watch", help="Run scraper on a schedule")
    p_watch.add_argument("--interval", type=_positive_int, default=30, metavar="MIN",
                         help="Polling interval in minutes (default: 30)")

    # config
    sub.add_parser("config", help="Show current configuration")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "scrape":  cmd_scrape,
        "analyze": cmd_analyze,
        "watch":   cmd_watch,
        "config":  cmd_config,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
