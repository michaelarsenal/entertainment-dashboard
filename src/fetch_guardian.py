"""Fetch Guardian Film & TV reviews from the last 6 months (max 180 days)."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import html
import json
import os
from pathlib import Path
import re
from typing import Any

import requests

GUARDIAN_API_URL = "https://content.guardianapis.com/search"
TMDB_API_URL = "https://api.themoviedb.org/3"
MAX_LOOKBACK_DAYS = 180  # Hard 6-month cap per user requirement

SECTIONS = [
    ("film/film,tone/reviews", "Movie"),
    ("tv-and-radio/tv-and-radio,tone/reviews", "TV"),
]


def clamp_lookback_days(days: int) -> int:
    """Clamp lookback window between 1 and MAX_LOOKBACK_DAYS (6 months)."""
    return max(1, min(days, MAX_LOOKBACK_DAYS))


def strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities from Guardian trailText."""
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", text)
    return html.unescape(cleaned).strip()


def extract_title(headline: str) -> str:
    """Extract clean Movie/TV title from Guardian review headlines.

    Examples:
        "The Glass Harbour review – luminous coastal mystery" -> "The Glass Harbour"
        "Severance season 3 review: sharper than ever" -> "Severance season 3"
    """
    if not headline:
        return "Untitled"
    match = re.split(r"\s+review\b(?:\s*[–—:\-])?", headline, maxsplit=1, flags=re.IGNORECASE)
    title = match[0].strip() if match else headline.strip()
    return title or headline.strip()


def normalize_guardian_item(item: dict[str, Any], media_type: str) -> dict[str, Any] | None:
    """Normalize a single Guardian API result into our dashboard schema."""
    fields = item.get("fields") or {}
    raw_stars = fields.get("starRating")
    if raw_stars is None:
        return None
    try:
        stars = int(raw_stars)
    except (TypeError, ValueError):
        return None

    pub_date = (item.get("webPublicationDate") or "")[:10]
    headline = fields.get("headline") or item.get("webTitle") or ""
    title = extract_title(headline)
    verdict = strip_html(fields.get("trailText") or "")
    critic = fields.get("byline") or "The Guardian"
    guardian_url = fields.get("shortUrl") or item.get("webUrl") or "https://www.theguardian.com"
    thumbnail = fields.get("thumbnail") or ""

    return {
        "id": item.get("id") or f"g-{pub_date}-{title.lower().replace(' ', '-')}",
        "title": title,
        "headline": headline,
        "type": media_type,
        "stars": max(1, min(5, stars)),
        "critic": critic,
        "reviewDate": pub_date,
        "releaseDate": pub_date,
        "platform": "UK Cinemas / Streaming" if media_type == "Movie" else "UK TV / Streaming",
        "genre": media_type,
        "runtime": "",
        "posterUrl": "",
        "trailerUrl": "",
        "verdict": verdict,
        "guardianUrl": guardian_url,
        "thumbnail": thumbnail,
        "ticketEvent": None,
    }


def format_runtime(minutes: int | None) -> str:
    """Format runtime in minutes as compact '1h 58m' or '45m'."""
    if not minutes or minutes <= 0:
        return ""
    hrs, mins = divmod(int(minutes), 60)
    if hrs and mins:
        return f"{hrs}h {mins}m"
    if hrs:
        return f"{hrs}h"
    return f"{mins}m"


def enrich_with_tmdb(review: dict[str, Any], tmdb_key: str, session: requests.Session) -> dict[str, Any]:
    """Optionally enrich a review with TMDB poster, genre, runtime, trailer, release date, and UK providers."""
    endpoint = "movie" if review["type"] == "Movie" else "tv"
    try:
        search_resp = session.get(
            f"{TMDB_API_URL}/search/{endpoint}",
            params={"api_key": tmdb_key, "query": review["title"], "region": "GB"},
            timeout=10,
        )
        search_resp.raise_for_status()
        results = search_resp.json().get("results") or []
        if not results:
            return review

        top = results[0]
        tmdb_id = top["id"]
        rel_date = top.get("release_date") or top.get("first_air_date")
        if rel_date:
            review["releaseDate"] = rel_date

        poster_path = top.get("poster_path")
        if poster_path:
            review["posterUrl"] = f"https://image.tmdb.org/t/p/w185{poster_path}"

        detail_resp = session.get(
            f"{TMDB_API_URL}/{endpoint}/{tmdb_id}",
            params={"api_key": tmdb_key, "append_to_response": "watch/providers,videos"},
            timeout=10,
        )
        detail_resp.raise_for_status()
        details = detail_resp.json()

        if not review["posterUrl"] and details.get("poster_path"):
            review["posterUrl"] = f"https://image.tmdb.org/t/p/w185{details['poster_path']}"

        genres = [g["name"] for g in (details.get("genres") or []) if g.get("name")]
        if genres:
            review["genre"] = " / ".join(genres[:2])

        if endpoint == "movie":
            review["runtime"] = format_runtime(details.get("runtime"))
        else:
            ep_times = details.get("episode_run_time") or []
            if ep_times:
                review["runtime"] = f"{format_runtime(ep_times[0])}/ep"
            elif details.get("number_of_seasons"):
                seasons = details["number_of_seasons"]
                review["runtime"] = f"{seasons} season{'s' if seasons != 1 else ''}"

        videos = (details.get("videos") or {}).get("results") or []
        yt_videos = [v for v in videos if v.get("site") == "YouTube" and v.get("key")]
        trailer = next((v for v in yt_videos if v.get("type") == "Trailer"), None) or (yt_videos[0] if yt_videos else None)
        if trailer:
            review["trailerUrl"] = f"https://www.youtube.com/watch?v={trailer['key']}"

        gb = ((details.get("watch/providers") or {}).get("results") or {}).get("GB") or {}
        flatrate = [p["provider_name"] for p in (gb.get("flatrate") or [])]
        if flatrate:
            review["platform"] = ", ".join(flatrate[:3])
    except requests.RequestException:
        pass
    return review


def fetch_guardian_reviews(
    api_key: str,
    days: int = MAX_LOOKBACK_DAYS,
    tmdb_key: str | None = None,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Fetch all Guardian Film & TV reviews within the clamped lookback window."""
    lookback = clamp_lookback_days(days)
    end_dt = today or date.today()
    start_dt = end_dt - timedelta(days=lookback)
    from_str = start_dt.isoformat()
    to_str = end_dt.isoformat()

    session = requests.Session()
    all_reviews: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for tag, media_type in SECTIONS:
        page = 1
        total_pages = 1
        while page <= total_pages:
            resp = session.get(
                GUARDIAN_API_URL,
                params={
                    "tag": tag,
                    "from-date": from_str,
                    "to-date": to_str,
                    "order-by": "newest",
                    "page-size": 200,
                    "page": page,
                    "show-fields": "starRating,headline,trailText,thumbnail,byline,shortUrl",
                    "api-key": api_key,
                },
                timeout=20,
            )
            resp.raise_for_status()
            body = resp.json().get("response") or {}
            total_pages = int(body.get("pages") or 1)
            for raw_item in body.get("results") or []:
                norm = normalize_guardian_item(raw_item, media_type)
                if not norm or norm["id"] in seen_ids:
                    continue
                if norm["reviewDate"] < from_str:
                    continue
                seen_ids.add(norm["id"])
                if tmdb_key:
                    norm = enrich_with_tmdb(norm, tmdb_key, session)
                all_reviews.append(norm)
            page += 1

    all_reviews.sort(key=lambda r: r["reviewDate"], reverse=True)
    return all_reviews


def demo_reviews(today: date | None = None) -> list[dict[str, Any]]:
    """Return realistic 6-month sample reviews when GUARDIAN_API_KEY is not configured."""
    ref = today or date.today()

    def d(offset_days: int) -> str:
        return (ref + timedelta(days=offset_days)).isoformat()

    return [
        {
            "id": "demo-101",
            "title": "The Glass Harbour",
            "type": "Movie",
            "stars": 5,
            "critic": "Peter Bradshaw",
            "reviewDate": d(-1),
            "releaseDate": d(2),
            "platform": "UK Cinemas & BFI Southbank",
            "genre": "Drama / Mystery",
            "verdict": "A luminous, haunting coastal mystery anchored by a career-best central performance.",
            "guardianUrl": "https://www.theguardian.com/film",
            "ticketEvent": {"type": "General Sale", "date": d(1), "venue": "BFI Southbank & Curzon", "note": "Q&A tickets release 10:00 GMT"},
        },
        {
            "id": "demo-102",
            "title": "Severance: Season 3",
            "type": "TV",
            "stars": 5,
            "critic": "Lucy Mangan",
            "reviewDate": d(-2),
            "releaseDate": d(3),
            "platform": "Apple TV+",
            "genre": "Sci-Fi / Thriller",
            "verdict": "Sharper, stranger and even more nerve-shredding than before.",
            "guardianUrl": "https://www.theguardian.com/tv-and-radio",
            "ticketEvent": None,
        },
        {
            "id": "demo-103",
            "title": "Midnight at Soho",
            "type": "Movie",
            "stars": 4,
            "critic": "Wendy Ide",
            "reviewDate": d(-3),
            "releaseDate": d(9),
            "platform": "UK Cinemas",
            "genre": "Noir / Music",
            "verdict": "Neon-drenched 1970s London jazz thriller that swings with undeniable style.",
            "guardianUrl": "https://www.theguardian.com/film",
            "ticketEvent": {"type": "Presale", "date": d(4), "venue": "Picturehouse Central", "note": "Members priority booking 09:00 GMT"},
        },
        {
            "id": "demo-104",
            "title": "The North Sea Line",
            "type": "TV",
            "stars": 5,
            "critic": "Jack Seale",
            "reviewDate": d(-4),
            "releaseDate": d(0),
            "platform": "BBC iPlayer / BBC One",
            "genre": "Crime / Documentary",
            "verdict": "Taut, compassionate and deeply gripping public-service drama.",
            "guardianUrl": "https://www.theguardian.com/tv-and-radio",
            "ticketEvent": None,
        },
        {
            "id": "demo-105",
            "title": "The Salt Road",
            "type": "Movie",
            "stars": 5,
            "critic": "Peter Bradshaw",
            "reviewDate": d(-23),
            "releaseDate": d(-19),
            "platform": "MUBI",
            "genre": "Documentary",
            "verdict": "Hypnotic, visually staggering portrait of ancient trade routes across the Sahara.",
            "guardianUrl": "https://www.theguardian.com/film",
            "ticketEvent": None,
        },
        {
            "id": "demo-106",
            "title": "Dept. Q: Copenhagen",
            "type": "TV",
            "stars": 4,
            "critic": "Jack Seale",
            "reviewDate": d(-41),
            "releaseDate": d(-38),
            "platform": "Netflix",
            "genre": "Nordic Noir",
            "verdict": "Moody, methodical cold-case thriller that rewards binge-watching.",
            "guardianUrl": "https://www.theguardian.com/tv-and-radio",
            "ticketEvent": None,
        },
        {
            "id": "demo-107",
            "title": "A Quiet Riot",
            "type": "Movie",
            "stars": 5,
            "critic": "Wendy Ide",
            "reviewDate": d(-76),
            "releaseDate": d(-72),
            "platform": "UK Cinemas & BFI Player",
            "genre": "Drama / LFF Pick",
            "verdict": "Fierce, tender and unforgettable—one of the standout British debuts of the year.",
            "guardianUrl": "https://www.theguardian.com/film",
            "ticketEvent": None,
        },
        {
            "id": "demo-108",
            "title": "Summer of 79",
            "type": "Movie",
            "stars": 4,
            "critic": "Peter Bradshaw",
            "reviewDate": d(-166),
            "releaseDate": d(-159),
            "platform": "BBC iPlayer / BBC Two",
            "genre": "Music / Documentary",
            "verdict": "Exhilarating archive-driven chronicle of the post-punk explosion.",
            "guardianUrl": "https://www.theguardian.com/film",
            "ticketEvent": None,
        },
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Guardian Film & TV reviews (up to 6 months).")
    parser.add_argument("--days", type=int, default=MAX_LOOKBACK_DAYS, help="Lookback days (max 180).")
    parser.add_argument("--out", type=Path, default=Path("data/reviews.json"), help="Output JSON path.")
    parser.add_argument("--demo", action="store_true", help="Write demo dataset instead of calling live API.")
    args = parser.parse_args()

    api_key = os.environ.get("GUARDIAN_API_KEY", "").strip()
    tmdb_key = os.environ.get("TMDB_API_KEY", "").strip() or None
    lookback = clamp_lookback_days(args.days)

    if args.demo or not api_key:
        mode = "demo"
        if not args.demo and not api_key:
            print("GUARDIAN_API_KEY not set; generating 6-month demo dataset.")
        reviews = demo_reviews()
    else:
        mode = "live"
        reviews = fetch_guardian_reviews(api_key=api_key, days=lookback, tmdb_key=tmdb_key)
        print(f"Fetched {len(reviews)} Guardian reviews from the last {lookback} days.")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": date.today().isoformat(),
        "lookbackDays": lookback,
        "mode": mode,
        "count": len(reviews),
        "reviews": reviews,
    }
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.out} ({len(reviews)} reviews, mode={mode}).")


if __name__ == "__main__":
    main()
