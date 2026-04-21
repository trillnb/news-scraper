"""
Tests for scraper.py, parser.py, and analyze.py.
Run with: pytest tests.py -v
"""
import argparse
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hn_html(articles: list[dict]) -> str:
    """Build minimal HN-shaped HTML from a list of article dicts."""
    rows = []
    for a in articles:
        comments_text = f"{a.get('comments', 0)} comments"
        rows.append(f"""
        <tr class="athing" id="{a['id']}">
          <td class="title">
            <span class="titleline">
              <a href="{a['link']}">{a['title']}</a>
            </span>
          </td>
        </tr>
        <tr>
          <td class="subtext">
            <span class="score" id="score_{a['id']}">{a['score']} points</span>
            by <a class="hnuser">{a['author']}</a>
            <span class="age" title="{a.get('posted_at', '')}">2 hours ago</span>
            | <a href="item?id={a['id']}">{comments_text}</a>
          </td>
        </tr>
        """)
    return f"<html><body><table>{''.join(rows)}</table></body></html>"


SAMPLE_ARTICLES = [
    {
        "id": "10001",
        "title": "Article Alpha",
        "link": "https://alpha.example.com",
        "score": 200,
        "comments": 42,
        "author": "alice",
        "posted_at": "2026-04-22T10:00:00 123456",
    },
    {
        "id": "10002",
        "title": "Article Beta",
        "link": "https://beta.example.com",
        "score": 80,
        "comments": 5,
        "author": "bob",
        "posted_at": "2026-04-22T14:30:00 123457",
    },
]

SAMPLE_HTML = _make_hn_html(SAMPLE_ARTICLES)


# ===========================================================================
# scraper.py
# ===========================================================================

from scraper import fetch_articles, load_config, _positive_int, HN_URL


class TestFetchArticles:

    def _mock_response(self, html: str) -> MagicMock:
        resp = MagicMock()
        resp.text = html
        resp.raise_for_status.return_value = None
        return resp

    @patch("scraper.requests.get")
    def test_returns_parsed_articles(self, mock_get):
        mock_get.return_value = self._mock_response(SAMPLE_HTML)
        articles = fetch_articles(limit=5)
        assert len(articles) == 2
        assert articles[0]["title"] == "Article Alpha"
        assert articles[0]["score"] == 200
        assert articles[0]["author"] == "alice"
        assert articles[0]["comments"] == 42
        assert articles[0]["link"] == "https://alpha.example.com"
        assert articles[0]["posted_at"] == "2026-04-22T10:00:00 123456"

    @patch("scraper.requests.get")
    def test_internal_link_gets_hn_prefix(self, mock_get):
        html = _make_hn_html([{
            "id": "99999",
            "title": "Internal",
            "link": "item?id=99999",
            "score": 10,
            "comments": 0,
            "author": "x",
        }])
        mock_get.return_value = self._mock_response(html)
        articles = fetch_articles(limit=1)
        assert articles[0]["link"] == HN_URL + "item?id=99999"

    @patch("scraper.requests.get")
    def test_missing_score_defaults_to_zero(self, mock_get):
        html = """
        <html><body><table>
          <tr class="athing" id="55555">
            <td class="title">
              <span class="titleline"><a href="https://x.com">No Score</a></span>
            </td>
          </tr>
          <tr>
            <td class="subtext">
              by <a class="hnuser">carol</a>
              <span class="age" title=""></span>
              | <a href="item?id=55555">3 comments</a>
            </td>
          </tr>
        </table></body></html>
        """
        mock_get.return_value = self._mock_response(html)
        articles = fetch_articles(limit=1)
        assert articles[0]["score"] == 0

    @patch("scraper.requests.get")
    def test_missing_author_defaults_to_unknown(self, mock_get):
        html = """
        <html><body><table>
          <tr class="athing" id="66666">
            <td class="title">
              <span class="titleline"><a href="https://y.com">No Author</a></span>
            </td>
          </tr>
          <tr>
            <td class="subtext">
              <span class="score" id="score_66666">50 points</span>
              <span class="age" title=""></span>
            </td>
          </tr>
        </table></body></html>
        """
        mock_get.return_value = self._mock_response(html)
        articles = fetch_articles(limit=1)
        assert articles[0]["author"] == "unknown"

    @patch("scraper.requests.get")
    def test_limit_cap_at_hn_page_limit(self, mock_get, capsys):
        mock_get.return_value = self._mock_response(SAMPLE_HTML)
        fetch_articles(limit=999)
        out = capsys.readouterr().out
        assert "capping" in out

    @patch("scraper.requests.get")
    def test_connection_error_raises_system_exit(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError()
        with pytest.raises(SystemExit, match="could not reach"):
            fetch_articles()

    @patch("scraper.requests.get")
    def test_timeout_raises_system_exit(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout()
        with pytest.raises(SystemExit, match="timed out"):
            fetch_articles()

    @patch("scraper.requests.get")
    def test_http_error_raises_system_exit(self, mock_get):
        error_response = MagicMock()
        error_response.status_code = 503
        mock_get.return_value.raise_for_status.side_effect = (
            requests.exceptions.HTTPError(response=error_response)
        )
        with pytest.raises(SystemExit, match="503"):
            fetch_articles()


class TestLoadConfig:

    def test_returns_empty_dict_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert load_config() == {}

    def test_loads_valid_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg = {"limit": 10, "min_score": 50, "output_file": "out.json"}
        (tmp_path / "config.json").write_text(json.dumps(cfg))
        assert load_config() == cfg

    def test_malformed_json_raises_system_exit(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.json").write_text("{not valid json")
        with pytest.raises(SystemExit, match="not valid JSON"):
            load_config()


class TestPositiveInt:

    def test_valid_value(self):
        assert _positive_int("5") == 5
        assert _positive_int("1") == 1

    def test_zero_raises(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _positive_int("0")

    def test_negative_raises(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _positive_int("-3")


# ===========================================================================
# parser.py
# ===========================================================================

from parser import filter_by_score, save_json, save_csv, process_articles


class TestFilterByScore:

    def test_keeps_articles_above_threshold(self):
        articles = [{"score": 50}, {"score": 100}, {"score": 150}]
        result = filter_by_score(articles, 100)
        assert len(result) == 2
        assert all(a["score"] >= 100 for a in result)

    def test_empty_list(self):
        assert filter_by_score([], 100) == []

    def test_nothing_passes_threshold(self):
        articles = [{"score": 10}, {"score": 20}]
        assert filter_by_score(articles, 100) == []

    def test_threshold_zero_keeps_all(self):
        articles = [{"score": 0}, {"score": 5}]
        assert filter_by_score(articles, 0) == articles


class TestSaveJson:

    def test_creates_file(self, tmp_path):
        path = tmp_path / "out.json"
        save_json([{"title": "A"}], path)
        assert path.exists()
        assert json.loads(path.read_text()) == [{"title": "A"}]

    def test_creates_backup_on_second_save(self, tmp_path):
        path = tmp_path / "out.json"
        save_json([{"score": 1}], path)
        save_json([{"score": 2}], path)
        backup = tmp_path / "out_prev.json"
        assert backup.exists()
        assert json.loads(backup.read_text())[0]["score"] == 1

    def test_os_error_raises_system_exit(self, tmp_path):
        path = tmp_path / "no_dir" / "out.json"
        with pytest.raises(SystemExit, match="could not write"):
            save_json([{"title": "X"}], path)


class TestSaveCsv:

    def test_creates_file_with_header(self, tmp_path):
        path = tmp_path / "out.csv"
        articles = [{"title": "T", "link": "http://x.com", "score": 10,
                     "comments": 1, "author": "a", "posted_at": ""}]
        save_csv(articles, path)
        lines = path.read_text().splitlines()
        assert "title" in lines[0]
        assert "T" in lines[1]

    def test_skips_empty_list(self, tmp_path):
        path = tmp_path / "out.csv"
        save_csv([], path)
        assert not path.exists()

    def test_missing_posted_at_uses_empty_string(self, tmp_path):
        path = tmp_path / "out.csv"
        articles = [{"title": "T", "link": "http://x.com",
                     "score": 10, "comments": 0, "author": "a"}]
        save_csv(articles, path)
        content = path.read_text()
        assert "T" in content


# ===========================================================================
# analyze.py
# ===========================================================================

from analyze import (
    load_data, load_prev_data, _parse_time, _truncate,
    compare_runs, avg_score, score_histogram,
)


class TestParseTime:

    def test_valid_iso_with_unix_suffix(self):
        dt = _parse_time("2026-04-22T10:00:00 123456")
        assert isinstance(dt, datetime)
        assert dt.hour == 10

    def test_valid_iso_only(self):
        dt = _parse_time("2026-04-22T14:30:00")
        assert dt is not None
        assert dt.hour == 14

    def test_empty_string_returns_none(self):
        assert _parse_time("") is None

    def test_whitespace_only_returns_none(self):
        assert _parse_time("   ") is None

    def test_invalid_format_returns_none(self):
        assert _parse_time("not-a-date") is None


class TestTruncate:

    def test_short_string_unchanged(self):
        assert _truncate("hello", 10) == "hello"

    def test_exact_length_unchanged(self):
        assert _truncate("hello", 5) == "hello"

    def test_long_string_truncated(self):
        result = _truncate("hello world", 8)
        assert result == "hello..."
        assert len(result) == 8

    def test_default_max_len(self):
        long = "x" * 60
        result = _truncate(long)
        assert result.endswith("...")
        assert len(result) == 52


class TestLoadData:

    def test_missing_file_exits(self, tmp_path):
        with pytest.raises(SystemExit, match="not found"):
            load_data(tmp_path / "nope.json")

    def test_empty_list_exits(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text("[]")
        with pytest.raises(SystemExit, match="empty"):
            load_data(p)

    def test_invalid_json_exits(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text("{bad json")
        with pytest.raises(SystemExit, match="invalid JSON"):
            load_data(p)

    def test_valid_file_returns_list(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text(json.dumps([{"score": 1}]))
        data = load_data(p)
        assert data == [{"score": 1}]


class TestLoadPrevData:

    def test_missing_file_returns_none(self, tmp_path):
        assert load_prev_data(tmp_path / "nope.json") is None

    def test_malformed_json_returns_none(self, tmp_path):
        p = tmp_path / "prev.json"
        p.write_text("{bad")
        assert load_prev_data(p) is None

    def test_valid_file_returns_list(self, tmp_path):
        p = tmp_path / "prev.json"
        p.write_text(json.dumps([{"score": 5}]))
        assert load_prev_data(p) == [{"score": 5}]

    def test_empty_list_returns_none(self, tmp_path):
        p = tmp_path / "prev.json"
        p.write_text("[]")
        assert load_prev_data(p) is None


class TestCompareRuns:

    def _article(self, link: str, title: str, score: int) -> dict:
        return {"link": link, "title": title, "score": score,
                "author": "x", "comments": 0, "posted_at": ""}

    def test_new_articles_reported(self, capsys):
        current = [self._article("http://new.com", "New One", 100)]
        previous = []
        compare_runs(current, previous)
        assert "+ 1 new article" in capsys.readouterr().out

    def test_gone_articles_reported(self, capsys):
        current = []
        previous = [self._article("http://old.com", "Old One", 50)]
        compare_runs(current, previous)
        assert "left the top" in capsys.readouterr().out

    def test_score_increase_reported(self, capsys):
        current  = [self._article("http://a.com", "A", 150)]
        previous = [self._article("http://a.com", "A", 100)]
        compare_runs(current, previous)
        out = capsys.readouterr().out
        assert "↑" in out
        assert "+50" in out

    def test_score_drop_reported(self, capsys):
        current  = [self._article("http://a.com", "A", 80)]
        previous = [self._article("http://a.com", "A", 100)]
        compare_runs(current, previous)
        out = capsys.readouterr().out
        assert "↓" in out
        assert "-20" in out

    def test_no_changes_reported(self, capsys):
        article = self._article("http://a.com", "A", 100)
        compare_runs([article], [article.copy()])
        assert "No changes" in capsys.readouterr().out


class TestAvgScore:

    def test_calculates_correctly(self, capsys):
        articles = [{"score": 100}, {"score": 200}, {"score": 300}]
        avg_score(articles)
        out = capsys.readouterr().out
        assert "200.0" in out
        assert "300" in out
        assert "100" in out


class TestScoreHistogram:

    def test_uniform_scores(self, capsys):
        articles = [{"score": 42}] * 3
        score_histogram(articles)
        assert "42" in capsys.readouterr().out

    def test_spread_scores(self, capsys):
        articles = [{"score": s} for s in [100, 200, 300, 400]]
        score_histogram(articles)
        out = capsys.readouterr().out
        assert "Bucket size" in out
        assert "█" in out
