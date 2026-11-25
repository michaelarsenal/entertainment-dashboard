"""Unit tests for Guardian fetcher and dashboard builder."""

from datetime import date
import json
from pathlib import Path

from src.build_dashboard import build_dashboard
from src.fetch_guardian import (
    MAX_LOOKBACK_DAYS,
    clamp_lookback_days,
    demo_reviews,
    extract_title,
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
