# Entertainment Dashboard

A static, auto-updating Film & TV reviews dashboard powered by **The Guardian Open Platform API** (6-month rolling window) with optional **TMDB** UK platform/release enrichment, one-click **Google Calendar** reminders, and a browser-persisted watchlist.

## Setup (CLI-First)

1. Get a free Guardian Open Platform API key at <https://open-platform.theguardian.com/access/>.
2. (Optional) Get a free TMDB API key at <https://www.themoviedb.org/settings/api> for UK streaming platform & release-date enrichment.
3. Set your GitHub repository secrets:
   ```bash
   gh secret set GUARDIAN_API_KEY --repo michaelarsenal/entertainment-dashboard
   gh secret set TMDB_API_KEY --repo michaelarsenal/entertainment-dashboard
   ```
4. Enable GitHub Pages (Source: **GitHub Actions**) in repository Settings -> Pages, then run the **Entertainment Dashboard** workflow.

## Local Run

```bash
pip install -r requirements.txt
pytest
python -m src.fetch_guardian --days 180 --out data/reviews.json
python -m src.build_dashboard --data data/reviews.json --out dist/index.html
```
