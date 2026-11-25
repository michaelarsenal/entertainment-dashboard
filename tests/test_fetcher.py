"""Unit tests for Guardian fetcher and dashboard builder."""

from datetime import date
import json
from pathlib import Path

from unittest.mock import MagicMock

from src.build_dashboard import build_dashboard
from src.fetch_guardian import (
    MAX_LOOKBACK_DAYS,
    clamp_lookback_days,
    demo_reviews,
    enrich_with_tmdb,
    extract_title,
    format_runtime,
    normalize_guardian_item,
)


def test_clamp_lookback_days_enforces_six_month_cap():
    assert clamp_lookback_days(30) == 30
    assert clamp_lookback_days(180) == MAX_LOOKBACK_DAYS
    assert clamp_lookback_days(365) == MAX_LOOKBACK_DAYS
    assert clamp_lookback_days(0) == 1


def test_extract_title_strips_review_suffix():
    assert extract_title("The Glass Harbour review – luminous coastal mystery") == "The Glass Harbour"
    assert extract_title("Severance season 3 review: sharper than ever") == "Severance season 3"
    assert extract_title("Plain Title") == "Plain Title"


def test_normalize_guardian_item_parses_star_rating():
    raw = {
        "id": "film/2026/nov/24/glass-harbour-review",
        "webPublicationDate": "2026-11-24T12:00:00Z",
        "webUrl": "https://www.theguardian.com/film/test",
        "fields": {
            "headline": "The Glass Harbour review – gripping",
            "starRating": "5",
            "trailText": "<p>Unmissable <strong>cinema</strong>.</p>",
            "byline": "Peter Bradshaw",
            "shortUrl": "https://gu.com/p/123",
        },
    }
    norm = normalize_guardian_item(raw, "Movie")
    assert norm is not None
    assert norm["title"] == "The Glass Harbour"
    assert norm["stars"] == 5
    assert norm["type"] == "Movie"
    assert norm["reviewDate"] == "2026-11-24"
    assert norm["verdict"] == "Unmissable cinema."
    assert norm["guardianUrl"] == "https://gu.com/p/123"


def test_demo_reviews_respect_six_month_window():
    ref = date(2026, 11, 25)
    reviews = demo_reviews(today=ref)
    assert len(reviews) >= 5
    for r in reviews:
        rev_dt = date.fromisoformat(r["reviewDate"])
        assert (ref - rev_dt).days <= MAX_LOOKBACK_DAYS


def test_build_dashboard_generates_html(tmp_path: Path):
    data_file = tmp_path / "reviews.json"
    out_file = tmp_path / "index.html"
    data_file.write_text(
        json.dumps(
            {
                "generatedAt": "2026-11-25",
                "lookbackDays": 180,
                "mode": "live",
                "reviews": demo_reviews(today=date(2026, 11, 25)),
            }
        ),
        encoding="utf-8",
    )
    result = build_dashboard(data_file, out_file)
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "LIVE GUARDIAN API" in content
    assert "calendar.google.com/calendar/render" in content
    assert "The Glass Harbour" in content


def test_format_runtime():
    assert format_runtime(118) == "1h 58m"
    assert format_runtime(120) == "2h"
    assert format_runtime(45) == "45m"
    assert format_runtime(None) == ""


def test_enrich_with_tmdb_populates_poster_genre_runtime_trailer_and_platform():
    search_resp = MagicMock()
    search_resp.json.return_value = {
        "results": [{"id": 999, "release_date": "2026-11-27", "poster_path": "/abc.jpg"}]
    }
    detail_resp = MagicMock()
    detail_resp.json.return_value = {
        "genres": [{"name": "Drama"}, {"name": "Mystery"}],
        "runtime": 118,
        "videos": {"results": [{"site": "YouTube", "type": "Trailer", "key": "xyz123"}]},
        "watch/providers": {"results": {"GB": {"flatrate": [{"provider_name": "MUBI"}]}}},
    }
    session = MagicMock()
    session.get.side_effect = [search_resp, detail_resp]

    review = {
        "title": "The Glass Harbour",
        "type": "Movie",
        "releaseDate": "2026-11-24",
        "platform": "UK Cinemas / Streaming",
        "genre": "Movie",
        "runtime": "",
        "posterUrl": "",
        "trailerUrl": "",
    }
    enriched = enrich_with_tmdb(review, "fake-key", session)
    assert enriched["releaseDate"] == "2026-11-27"
    assert enriched["posterUrl"] == "https://image.tmdb.org/t/p/w185/abc.jpg"
    assert enriched["genre"] == "Drama / Mystery"
    assert enriched["runtime"] == "1h 58m"
    assert enriched["trailerUrl"] == "https://www.youtube.com/watch?v=xyz123"
    assert enriched["platform"] == "MUBI"
