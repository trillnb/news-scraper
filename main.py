import argparse
import json
import sys
from datetime import datetime, timezone
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


def cmd_report(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    articles = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(articles, list):
        print("Error: input JSON must be a list of articles.", file=sys.stderr)
        sys.exit(1)

    fmt = args.format.lower()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if fmt == "md":
        output_path = Path(args.output) if args.output else Path("report.md")
        lines = [
            f"# News Digest",
            f"",
            f"_Generated: {generated_at} — {len(articles)} articles_",
            f"",
        ]
        for i, a in enumerate(articles, 1):
            title     = a.get("title", "Untitled")
            link      = a.get("link", "")
            score     = a.get("score", "—")
            author    = a.get("author", "unknown")
            posted_at = a.get("posted_at", "")[:19]  # trim unix suffix
            comments  = a.get("comments", 0)
            lines += [
                f"## {i}. [{title}]({link})",
                f"",
                f"- **Score:** {score} | **Author:** {author} | **Comments:** {comments}",
                f"- **Posted:** {posted_at}",
                f"",
            ]
        output_path.write_text("\n".join(lines), encoding="utf-8")

    elif fmt == "html":
        output_path = Path(args.output) if args.output else Path("report.html")
        rows = ""
        for i, a in enumerate(articles, 1):
            title     = a.get("title", "Untitled").replace("<", "&lt;").replace(">", "&gt;")
            link      = a.get("link", "#")
            score     = a.get("score", "—")
            author    = a.get("author", "unknown").replace("<", "&lt;")
            posted_at = a.get("posted_at", "")[:19]
            comments  = a.get("comments", 0)
            rows += (
                f"<tr>"
                f"<td>{i}</td>"
                f"<td><a href=\"{link}\">{title}</a></td>"
                f"<td>{score}</td>"
                f"<td>{author}</td>"
                f"<td>{comments}</td>"
                f"<td>{posted_at}</td>"
                f"</tr>\n"
            )
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>News Digest</title>
<style>
  body{{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#222}}
  h1{{font-size:1.6rem;margin-bottom:.25rem}}
  .meta{{color:#666;font-size:.875rem;margin-bottom:1.5rem}}
  table{{width:100%;border-collapse:collapse;font-size:.9rem}}
  th{{background:#f0f0f0;text-align:left;padding:.5rem .75rem;border-bottom:2px solid #ccc}}
  td{{padding:.45rem .75rem;border-bottom:1px solid #e0e0e0;vertical-align:top}}
  tr:hover td{{background:#fafafa}}
  a{{color:#1a6fc4;text-decoration:none}}
  a:hover{{text-decoration:underline}}
</style>
</head>
<body>
<h1>News Digest</h1>
<p class="meta">Generated: {generated_at} &mdash; {len(articles)} articles</p>
<table>
<thead><tr><th>#</th><th>Title</th><th>Score</th><th>Author</th><th>Comments</th><th>Posted</th></tr></thead>
<tbody>
{rows}</tbody>
</table>
</body>
</html>"""
        output_path.write_text(html, encoding="utf-8")

    else:
        print(f"Error: unknown format '{fmt}'. Use 'md' or 'html'.", file=sys.stderr)
        sys.exit(1)

    print(f"Report saved to {output_path.resolve()}")


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

    # report
    p_report = sub.add_parser("report", help="Export articles to Markdown or HTML")
    p_report.add_argument("--format", choices=["md", "html"], default="md", metavar="FMT",
                          help="Output format: md (default) or html")
    p_report.add_argument("--input", default="data.json", metavar="FILE",
                          help="Source JSON file (default: data.json)")
    p_report.add_argument("--output", default=None, metavar="FILE",
                          help="Destination file (default: report.md / report.html)")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "scrape":  cmd_scrape,
        "analyze": cmd_analyze,
        "watch":   cmd_watch,
        "config":  cmd_config,
        "report":  cmd_report,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
