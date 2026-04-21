import logging
import time
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("scraper.log")


def _setup_logging() -> None:
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def watch(interval_minutes: int, config: dict) -> None:
    _setup_logging()

    limit = config.get("limit", 30)
    min_score = config.get("min_score", 100)
    output = config.get("output_file", "data.json")

    print(f"Watching Hacker News every {interval_minutes} min  (Ctrl+C to stop)")
    print(f"Settings: limit={limit}, min-score={min_score}, output={output}")
    print(f"Logging to {LOG_FILE}\n")

    # Import here to avoid circular imports at module load time
    from scraper import fetch_articles
    from parser import process_articles

    run_number = 0
    while True:
        run_number += 1
        started = datetime.now().strftime("%H:%M:%S")
        print(f"[{started}] Run #{run_number} — scraping...", end=" ", flush=True)
        try:
            articles = fetch_articles(limit=limit)
            filtered_count = sum(1 for a in articles if a["score"] >= min_score)
            process_articles(articles, score_threshold=min_score, output=output)
            msg = (
                f"run={run_number} fetched={len(articles)} "
                f"filtered={filtered_count} output={output}"
            )
            logging.info(msg)
            print(f"done  ({filtered_count} articles saved)")
        except SystemExit as exc:
            logging.error(f"run={run_number} error={exc}")
            print(f"error: {exc}")
        except Exception as exc:
            logging.error(f"run={run_number} error={exc}")
            print(f"unexpected error: {exc}")

        print(f"  Next run in {interval_minutes} min — waiting…")
        time.sleep(interval_minutes * 60)
