# Morning Brief

> Your world. One feed.

A premium dark-theme Streamlit news dashboard that aggregates live headlines from 16 major news sources using RSS feeds — no API keys required.

## Sources

| Source | Feed Type |
|---|---|
| BBC News | Direct RSS |
| Reuters | Direct RSS |
| Sky News | Direct RSS |
| CNBC | Direct RSS |
| AP News | Direct RSS |
| CityAM | Direct RSS |
| Gulf News | Direct RSS |
| Khaleej Times | Direct RSS |
| NDTV | Direct RSS |
| CNN | Direct RSS |
| Forbes | Direct RSS |
| Financial Times | Direct RSS* |
| Telegraph | Direct RSS* |
| The Times | Google News RSS* |
| Bloomberg | Google News RSS* |
| The Economist | Direct RSS* |

\* **Subscription sources:** FT, Telegraph, The Times, Bloomberg, and The Economist require you to be logged in on your browser. The RSS feeds surface headlines; clicking a headline opens the full article on the publisher's site where your existing login session will authenticate you automatically. Bloomberg and The Times use Google News RSS, which surfaces their content reliably without needing a direct feed.

## Prerequisites

- Python 3.8+

## Installation

```bash
pip install -r requirements.txt
```

## Running the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

## Features

- **16 live sources** fetched concurrently via ThreadPoolExecutor
- **5-minute cache** to avoid hammering feeds
- **3-column card grid** with source colour coding
- **Real-time search** across headlines and descriptions
- **Category filter** (World News, Business/Finance, Technology, Politics)
- **Source filter** — toggle individual sources on/off
- **Auto-refresh** every 5 minutes with countdown timer
- **Relative timestamps** ("14 minutes ago", "2 hours ago")
- **Live/failed status dots** per source in sidebar
- **Dark editorial theme** with Google Fonts
