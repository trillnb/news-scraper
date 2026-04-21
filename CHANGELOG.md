# Changelog

All notable changes to this project are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.3.0] — 2026-04-22

### Added
- `main.py` — unified CLI entry point with four sub-commands:
  `scrape`, `analyze`, `watch`, `config`
- `config.json` — centralised defaults for `limit`, `min_score`,
  `output_file`, and `sources`; CLI flags override config values
- `scheduler.py` — `watch` mode that runs the scraper on a
  configurable interval and appends each result to `scraper.log`
  with timestamp, fetched/filtered counts, and output path

### Changed
- `scraper.py` now reads defaults from `config.json` when no CLI
  flags are provided (priority: CLI → config → built-in defaults)

---

## [0.2.0] — 2026-04-22

### Added
- `analyze.py` — reads `data.json` and prints:
  - average, highest, and lowest score
  - most prolific author in the current dataset
  - peak posting hour with a per-hour bar chart (UTC)
  - score distribution histogram rendered with `█` characters
- Diff report comparing the current run against `data_prev.json`:
  new articles, score increases, score drops, articles that left
  the top

---

## [0.1.0] — 2026-04-22

### Added
- `scraper.py` — fetches up to 30 stories from
  `news.ycombinator.com` (title, link, score, comments, author,
  timestamp) using `requests` + `BeautifulSoup`; validates
  `--limit` and `--min-score` arguments; handles timeouts,
  connection errors, and non-2xx responses with clean messages
- `parser.py` — filters articles by score threshold, saves to
  JSON and CSV, prints a top-5 table in the terminal; backs up
  the previous `data.json` to `data_prev.json` before each write
- `requirements.txt` — `requests` and `beautifulsoup4`
- `.gitignore` — excludes generated data files, logs, caches,
  and OS/IDE artefacts

---

## Planned Features

### 1. Multiple sources — Reddit, Lobsters, dev.to
The `sources` key already exists in `config.json` but only
`hackernews` is implemented. Adding adapters for other feeds
(Reddit `r/programming`, Lobste.rs, dev.to) behind a common
interface would let users aggregate tech news in one place.

### 2. SQLite storage with full history
Currently each run overwrites `data.json` and keeps only one
previous snapshot. Persisting every scrape to a local SQLite
database would enable trend queries: score velocity per article,
author activity over time, which topics stay in the top longest.

### 3. Keyword filtering and topic tagging
Allow users to define keywords or regex patterns in `config.json`
to include or exclude articles by title. Combined with automatic
tagging (AI, security, open-source, etc.) this would make the
tool useful as a personal news filter.

### 4. Telegram / email digest
A `notify` command that sends a formatted digest of the top
articles after each scheduled scrape — either via a Telegram bot
token or SMTP. Natural next step after `watch` mode already
produces structured log output.

### 5. Export to Markdown / HTML report
A `report` sub-command in `main.py` that renders `data.json`
into a readable Markdown or self-contained HTML file — useful for
sharing a daily digest as a file or publishing it as a static page.
