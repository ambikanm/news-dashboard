import streamlit as st
import streamlit.components.v1 as components
import feedparser
import requests
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import parsedate_to_datetime
import re

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="The Nilesh Times",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Source definitions ─────────────────────────────────────────────────────────
SOURCES = [
    {"name": "BBC News",        "url": "http://feeds.bbci.co.uk/news/rss.xml",                                               "colour": "#BB1919", "domain": "bbc.co.uk",         "text": "#fff"},
    {"name": "Reuters",         "url": "https://feeds.reuters.com/reuters/topNews",                                          "colour": "#FF8000", "domain": "reuters.com",        "text": "#fff"},
    {"name": "Sky News",        "url": "https://feeds.skynews.com/feeds/rss/home.xml",                                       "colour": "#003082", "domain": "skynews.com",        "text": "#fff"},
    {"name": "CNBC",            "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",                              "colour": "#0070C8", "domain": "cnbc.com",           "text": "#fff"},
    {"name": "AP News",         "url": "https://feeds.apnews.com/rss/apf-topnews",                                          "colour": "#333333", "domain": "apnews.com",         "text": "#fff"},
    {"name": "CityAM",          "url": "https://www.cityam.com/feed/",                                                      "colour": "#2E7D32", "domain": "cityam.com",         "text": "#fff"},
    {"name": "Gulf News",       "url": "https://gulfnews.com/rss",                                                          "colour": "#00796B", "domain": "gulfnews.com",       "text": "#fff"},
    {"name": "Khaleej Times",   "url": "https://www.khaleejtimes.com/rss",                                                  "colour": "#6A1B9A", "domain": "khaleejtimes.com",   "text": "#fff"},
    {"name": "NDTV",            "url": "https://feeds.feedburner.com/ndtvnews-top-stories",                                  "colour": "#8B0000", "domain": "ndtv.com",           "text": "#fff"},
    {"name": "CNN",             "url": "http://rss.cnn.com/rss/edition.rss",                                                "colour": "#CC0000", "domain": "cnn.com",            "text": "#fff"},
    {"name": "Forbes",          "url": "https://www.forbes.com/feeds/forbesmagazine/index.rss",                             "colour": "#1B5E20", "domain": "forbes.com",         "text": "#fff"},
    {"name": "Financial Times", "url": "https://www.ft.com/rss/home",                                                       "colour": "#D6580A", "domain": "ft.com",             "text": "#fff"},
    {"name": "Telegraph",       "url": "https://www.telegraph.co.uk/rss.xml",                                               "colour": "#1C3F6E", "domain": "telegraph.co.uk",    "text": "#fff"},
    {"name": "The Times",       "url": "https://news.google.com/rss/search?q=the+times+uk+news&hl=en-GB&gl=GB&ceid=GB:en", "colour": "#C41E3A", "domain": "thetimes.co.uk",     "text": "#fff"},
    {"name": "Bloomberg",       "url": "https://news.google.com/rss/search?q=bloomberg+finance&hl=en-GB&gl=GB&ceid=GB:en", "colour": "#444444", "domain": "bloomberg.com",      "text": "#fff"},
    {"name": "The Economist",   "url": "https://www.economist.com/rss/the-economist-today.rss",                             "colour": "#E3120B", "domain": "economist.com",      "text": "#fff"},
]

SOURCE_MAP = {s["name"]: s for s in SOURCES}

CATEGORY_KEYWORDS = {
    "Business / Finance": [
        "market", "stock", "share", "gdp", "inflation", "rate", "bank", "economy",
        "fund", "trading", "trade", "finance", "financial", "invest", "revenue",
        "profit", "earning", "bond", "yield", "currency", "dollar", "pound",
        "euro", "oil", "energy", "commodity", "recession", "growth",
    ],
    "Technology": [
        "ai", "artificial intelligence", "tech", "apple", "google", "microsoft",
        "amazon", "meta", "chip", "cyber", "software", "startup", "digital",
        "data", "robot", "automation", "cloud", "semiconductor", "openai",
        "nvidia", "elon", "tesla", "space", "satellite",
    ],
    "Politics": [
        "government", "election", "minister", "parliament", "senate", "congress",
        "president", "policy", "party", "vote", "democrat", "republican",
        "labour", "conservative", "prime minister", "white house", "kremlin",
        "nato", "un ", "united nations", "diplomat", "sanction", "treaty",
    ],
}

# ── CSS injection ──────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">

<style>
/* ── Reset & base ── */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* Grain texture overlay */
body::before {
    content: '';
    position: fixed;
    top: 0; left: 0;
    width: 100vw; height: 100vh;
    pointer-events: none;
    z-index: 9999;
    opacity: 0.018;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='1'/%3E%3C/svg%3E");
    background-repeat: repeat;
    background-size: 200px 200px;
}

/* ── Page background ── */
.stApp {
    background-color: #ffffff !important;
    color: #1a1a1a !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #f7f7f7 !important;
    border-right: 1px solid #e8e8e8 !important;
}
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
    color: #555555 !important;
}

/* Sidebar section headers */
.sidebar-section-header {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #aaaaaa !important;
    margin: 20px 0 8px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #e8e8e8;
}

/* ── Source dots ── */
.source-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 2px 0;
    font-size: 13px;
}
.dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
}
.dot-live  { background: #22c55e; box-shadow: 0 0 4px #22c55e88; }
.dot-fail  { background: #ef4444; box-shadow: 0 0 4px #ef444488; }

/* ── Header bar ── */
.morning-header {
    background: #ffffff;
    border-bottom: 1px solid #e8e8e8;
    padding: 28px 40px 22px 40px;
    margin: -1rem -1rem 0 -1rem;
    position: relative;
}
.morning-header::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #BB1919, #FF8000, #0070C8, #2E7D32, #6A1B9A);
}
.morning-title {
    font-size: 42px;
    font-weight: 800;
    letter-spacing: -1.5px;
    color: #1a1a1a;
    line-height: 1;
    margin: 0;
}
.morning-subtitle {
    font-size: 14px;
    font-weight: 400;
    color: #aaaaaa;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 6px;
}
.header-clock {
    font-size: 28px;
    font-weight: 300;
    color: #555555;
    font-variant-numeric: tabular-nums;
    letter-spacing: 1px;
}

/* ── Stats bar ── */
.stats-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 14px 0 18px 0;
    font-size: 13px;
    color: #aaaaaa;
    border-bottom: 1px solid #e8e8e8;
    margin-bottom: 20px;
}
.stats-count {
    font-size: 20px;
    font-weight: 700;
    color: #1a1a1a;
}
.stats-sep { color: #cccccc; }

/* ── Card grid ── */
.card-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    padding-bottom: 60px;
}
@media (max-width: 1100px) {
    .card-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 700px) {
    .card-grid { grid-template-columns: 1fr; }
}

/* ── Article card ── */
.news-card {
    background: #ffffff;
    border-radius: 10px;
    border: 1px solid #e8e8e8;
    border-left-width: 3px;
    padding: 16px 18px 14px 18px;
    transition: background 0.18s, box-shadow 0.18s;
    display: flex;
    flex-direction: column;
    gap: 8px;
    position: relative;
    overflow: hidden;
}
.news-card:hover {
    background: #fafafa;
    box-shadow: 0 2px 14px rgba(0,0,0,0.07);
}

.card-header {
    display: flex;
    align-items: center;
    gap: 8px;
}
.source-badge {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    padding: 3px 8px;
    border-radius: 100px;
    white-space: nowrap;
}
.card-favicon {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    object-fit: contain;
    flex-shrink: 0;
    margin-left: auto;
}
.card-title {
    font-size: 14px;
    font-weight: 600;
    line-height: 1.4;
    color: #1a1a1a;
}
.card-title a {
    color: #1a1a1a !important;
    text-decoration: none !important;
}
.card-title a:hover {
    color: #000000 !important;
    text-decoration: underline !important;
}
.card-desc {
    font-size: 12px;
    color: #888888;
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    flex: 1;
}
.card-footer {
    font-size: 11px;
    color: #bbbbbb;
    margin-top: 4px;
}

/* ── Streamlit widget overrides ── */
[data-testid="stCheckbox"] label span {
    font-size: 13px !important;
    color: #555555 !important;
}
.stSelectbox label, .stTextInput label {
    color: #888888 !important;
    font-size: 12px !important;
}
div[data-testid="stSelectbox"] > div {
    background: #f5f5f5 !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: 6px !important;
}
div[data-testid="stTextInput"] input {
    background: #f5f5f5 !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: 6px !important;
    color: #1a1a1a !important;
    font-size: 13px !important;
}
.stButton button {
    background: #f5f5f5 !important;
    border: 1px solid #e0e0e0 !important;
    color: #555555 !important;
    border-radius: 6px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    padding: 6px 16px !important;
    transition: background 0.15s, border-color 0.15s !important;
}
.stButton button:hover {
    background: #ebebeb !important;
    border-color: #cccccc !important;
    color: #333333 !important;
}

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden; }

/* ── Toggle ── */
[data-testid="stToggle"] label {
    color: #555555 !important;
    font-size: 13px !important;
}

/* ── No results ── */
.no-results {
    text-align: center;
    padding: 80px 20px;
    color: #bbbbbb;
    font-size: 14px;
}
.no-results-icon {
    font-size: 48px;
    display: block;
    margin-bottom: 12px;
    opacity: 0.4;
}

/* ── Countdown ── */
.countdown-text {
    font-size: 11px;
    color: #aaaaaa;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.5px;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f5f5f5; }
::-webkit-scrollbar-thumb { background: #d0d0d0; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #bbbbbb; }
</style>
""", unsafe_allow_html=True)

    # Clock script injected via components.html (st.markdown strips <script> tags).
    # Uses window.parent.document to reach the parent frame's DOM element.
    components.html("""
<script>
(function tick() {
    try {
        var el = window.parent.document.getElementById('mb-clock');
        if (el) {
            var now = new Date();
            el.textContent =
                String(now.getHours()).padStart(2,'0') + ':' +
                String(now.getMinutes()).padStart(2,'0') + ':' +
                String(now.getSeconds()).padStart(2,'0');
        }
    } catch(e) {}
    setTimeout(tick, 1000);
})();
</script>
""", height=0)


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_datetime(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return parsedate_to_datetime(val).astimezone(timezone.utc)
            except Exception:
                pass
    return None


def time_ago(dt: datetime | None) -> str:
    if dt is None:
        return "Unknown time"
    now = datetime.now(timezone.utc)
    diff = int((now - dt).total_seconds())
    if diff < 0:
        return "Just now"
    if diff < 60:
        return f"{diff}s ago"
    if diff < 3600:
        m = diff // 60
        return f"{m} minute{'s' if m != 1 else ''} ago"
    if diff < 86400:
        h = diff // 3600
        return f"{h} hour{'s' if h != 1 else ''} ago"
    d = diff // 86400
    return f"{d} day{'s' if d != 1 else ''} ago"


def truncate(text: str, chars: int = 180) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text).strip()
    return text[:chars] + "…" if len(text) > chars else text


def infer_category(title: str, desc: str) -> str:
    combined = (title + " " + (desc or "")).lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(kw in combined for kw in kws):
            return cat
    return "World News"


def fetch_feed(source: dict) -> tuple[str, list[dict], bool]:
    name = source["name"]
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; MorningBrief/1.0; +https://github.com/morning-brief)"}
        resp = requests.get(source["url"], headers=headers, timeout=10)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        articles = []
        for entry in feed.entries[:30]:
            title = getattr(entry, "title", "").strip()
            if not title:
                continue
            link  = getattr(entry, "link",    "") or ""
            desc  = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
            dt    = parse_datetime(entry)
            articles.append({
                "source":             name,
                "title":              title,
                "url":                link,
                "description":        truncate(desc, 200),
                "published_datetime": dt,
                "favicon_url":        f"https://www.google.com/s2/favicons?domain={source['domain']}&sz=32",
                "colour":             source["colour"],
                "text_colour":        source["text"],
            })
        return name, articles, True
    except Exception:
        return name, [], False


@st.cache_data(ttl=300, show_spinner=False)
def fetch_all_feeds() -> tuple[list[dict], dict[str, bool]]:
    all_articles: list[dict] = []
    status: dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=16) as ex:
        futures = {ex.submit(fetch_feed, s): s for s in SOURCES}
        for future in as_completed(futures):
            name, articles, ok = future.result()
            status[name] = ok
            all_articles.extend(articles)
    all_articles.sort(
        key=lambda a: a["published_datetime"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return all_articles, status


# ── Static HTML fragments ─────────────────────────────────────────────────────

# Pure div — no <script> tag (scripts are stripped by st.markdown).
# The clock JS is injected separately via components.html in inject_css().
CLOCK_DIV = '<div id="mb-clock" class="header-clock">--:--:--</div>'

NEWSPAPER_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36" fill="none"
     stroke="#999" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/>
  <path d="M18 14h-8M15 18h-5M10 6h8v4h-8z"/>
</svg>
"""


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar(status: dict[str, bool]) -> tuple[list[str], str, str, bool]:
    with st.sidebar:
        st.markdown(NEWSPAPER_SVG, unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:20px;font-weight:800;color:#1a1a1a;letter-spacing:-0.5px;margin:8px 0 4px 0'>The Nilesh Times</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='font-size:10px;color:#aaaaaa;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px'>Your world. One feed.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<hr style='border-color:#e8e8e8;margin:4px 0 0 0'>", unsafe_allow_html=True)

        # ── Refresh ──
        st.markdown("<div class='sidebar-section-header'>Refresh</div>", unsafe_allow_html=True)
        auto_refresh = st.toggle("Auto-refresh (5 min)", value=True)
        if st.button("⟳  Refresh Now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        # ── Sources ──
        st.markdown("<div class='sidebar-section-header'>Sources</div>", unsafe_allow_html=True)
        selected_sources: list[str] = []
        for src in SOURCES:
            dot_cls = "dot-live" if status.get(src["name"], False) else "dot-fail"
            checked = st.checkbox(src["name"], value=True, key=f"src_{src['name']}")
            if checked:
                selected_sources.append(src["name"])
            st.markdown(
                f"<div class='source-item' style='margin-top:-28px;pointer-events:none'>"
                f"<span class='dot {dot_cls}'></span></div>",
                unsafe_allow_html=True,
            )

        # ── Category ──
        st.markdown("<div class='sidebar-section-header'>Category</div>", unsafe_allow_html=True)
        category = st.selectbox(
            "Topic",
            ["All Topics", "World News", "Business / Finance", "Technology", "Politics"],
            label_visibility="collapsed",
        )

        # ── Search ──
        st.markdown("<div class='sidebar-section-header'>Search</div>", unsafe_allow_html=True)
        search = st.text_input("Search headlines…", placeholder="Search headlines…", label_visibility="collapsed")

    return selected_sources, category, search, auto_refresh


# ── Card renderer ─────────────────────────────────────────────────────────────

def card_html(article: dict) -> str:
    colour      = article["colour"]
    txt_colour  = article["text_colour"]
    source      = article["source"]
    title       = article["title"].replace('"', "&quot;").replace("<", "&lt;")
    url         = article["url"]
    desc        = article["description"].replace("<", "&lt;").replace(">", "&gt;")
    favicon     = article["favicon_url"]
    ago         = time_ago(article["published_datetime"])

    return f"""
<div class="news-card" style="border-left-color:{colour};">
  <div class="card-header">
    <span class="source-badge" style="background:{colour};color:{txt_colour};">{source}</span>
    <img class="card-favicon" src="{favicon}" alt="" onerror="this.style.display='none'">
  </div>
  <div class="card-title">
    <a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>
  </div>
  <div class="card-desc">{desc}</div>
  <div class="card-footer">{ago}</div>
</div>
"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    inject_css()

    # Auto-refresh trigger
    if AUTOREFRESH_AVAILABLE:
        if st.session_state.get("auto_refresh_enabled", True):
            st_autorefresh(interval=300_000, key="autorefresh_counter")

    # Fetch data
    with st.spinner("Fetching headlines…"):
        articles, status = fetch_all_feeds()

    # Sidebar (needs status for dots)
    selected_sources, category, search, auto_refresh = render_sidebar(status)
    st.session_state["auto_refresh_enabled"] = auto_refresh

    # ── Header ──
    last_refreshed = datetime.now().strftime("%H:%M:%S")
    st.markdown(f"""
<div class="morning-header">
  <div style="display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px">
    <div>
      <div class="morning-title">The Nilesh Times</div>
      <div class="morning-subtitle">Your world. One feed.</div>
    </div>
    <div style="text-align:right">
      {CLOCK_DIV}
      <div style="font-size:11px;color:#aaaaaa;margin-top:4px">Last updated {last_refreshed}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Filter articles ──
    filtered = articles

    if selected_sources:
        filtered = [a for a in filtered if a["source"] in selected_sources]

    if category != "All Topics":
        filtered = [a for a in filtered if infer_category(a["title"], a["description"]) == category]

    if search:
        q = search.lower()
        filtered = [
            a for a in filtered
            if q in a["title"].lower() or q in a["description"].lower()
        ]

    live_sources = sum(1 for v in status.values() if v)
    total = len(filtered)

    # ── Stats bar ──
    filter_tag = (
        f"<span class='stats-sep'>·</span><span style='color:#999'>filtered by: {category}</span>"
        if category != "All Topics" else ""
    )
    search_tag = (
        f"<span class='stats-sep'>·</span><span style='color:#999'>&ldquo;{search}&rdquo;</span>"
        if search else ""
    )
    st.markdown(f"""
<div class="stats-bar">
  <span class="stats-count">{total:,}</span>
  <span>headline{'s' if total != 1 else ''}</span>
  <span class="stats-sep">·</span>
  <span class="stats-count">{live_sources}</span>
  <span>of {len(SOURCES)} sources live</span>
  {filter_tag}{search_tag}
</div>
""", unsafe_allow_html=True)

    # ── Card grid ──
    if not filtered:
        st.markdown("""
<div class="no-results">
  <span class="no-results-icon">📭</span>
  No headlines match your filters.
</div>
""", unsafe_allow_html=True)
        return

    COLS = 3
    grid_cards = []
    for i in range(0, len(filtered), COLS):
        chunk = filtered[i:i + COLS]
        grid_cards.extend(card_html(a) for a in chunk)

    st.markdown(f'<div class="card-grid">{"".join(grid_cards)}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
