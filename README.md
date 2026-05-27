# The Nilesh Times

> The more you do, the more you can do.

A clean, white-theme Streamlit news dashboard that aggregates live headlines from 16 major news sources using RSS feeds — no API keys required.

Live at: **https://thenileshtimes.streamlit.app**

## Sources

| Source | Feed type |
|---|---|
| BBC News | Direct RSS |
| Reuters | Google News RSS |
| Sky News | Direct RSS |
| CNBC | Direct RSS |
| AP News | Google News RSS |
| CityAM | Google News RSS |
| Gulf News | Google News RSS |
| Khaleej Times | Google News RSS |
| NDTV | Direct RSS |
| CNN | Direct RSS |
| Forbes | Direct RSS |
| Financial Times | Direct RSS |
| Telegraph | Google News RSS |
| The Times | Google News RSS |
| Bloomberg | Google News RSS |
| The Economist | Direct RSS (section feed) |

Sources using Google News RSS had their direct feeds blocked (403/404) or retired — Google News surfaces their headlines reliably without requiring a direct publisher feed. Clicking any headline opens the article on the publisher's own site.

**Subscription sources:** FT, Telegraph, The Times, Bloomberg, and The Economist require you to be logged in on your browser. Headlines are always visible; clicking opens the publisher's site where your existing login session handles access automatically.

## Prerequisites

- Python 3.8+

## Installation

```bash
pip install -r requirements.txt
```

## Running locally

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`.

## Features

- **16 live sources** fetched concurrently (8 workers to avoid Google News throttling)
- **5-minute RSS cache** — feeds refresh automatically every 5 minutes
- **🔄 Refresh Now button** — clears cache and re-fetches all feeds on demand; appears in the sidebar, the mobile filter panel, and next to the headline count
- **3-column card grid** — responsive: 3 columns on desktop, 2 on tablet, 1 on mobile
- **Article cards** — source badge, favicon, clickable headline, summary, relative timestamp ("14 minutes ago")
- **Source colour coding** — each source has a distinct accent colour on card borders and badges
- **Real-time search** — filters cards instantly across headlines and descriptions
- **Category filter** — World News, Business / Finance, Technology, Politics (keyword-inferred)
- **Source filter** — toggle individual sources on/off with Select All / Deselect All buttons
- **Mobile filter expander** — collapsible Filter & Search panel at the top of the page for easy access on phones
- **Sidebar** — full filter controls for desktop users; stays in sync with the mobile expander via session state
- **Live/failed status dots** — green/red dot next to each source in the sidebar showing feed health
- **Auto-refresh** — optional 5-minute auto-refresh toggle
- **Live clock** — ticking clock in the header (JavaScript)
- **Last updated UTC** — header shows the exact UTC time the page last rendered
- **Light editorial theme** — clean white background, Plus Jakarta Sans font, subtle grain texture

## Deployment

The app is deployed on **Streamlit Community Cloud** (free tier).

To push updates:

```bash
git add .
git commit -m "describe what changed"
git push
```

Streamlit Cloud detects the push and redeploys in ~1 minute. The URL never changes.

**Note:** The app sleeps after ~7 days of no visits and wakes automatically (~30 seconds) when the URL is opened.
