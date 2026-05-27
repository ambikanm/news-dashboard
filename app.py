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
# Reuters, AP, CityAM, Gulf News, Khaleej Times, Telegraph moved to Google News
# RSS (direct feeds returned 403/404/timeout). The Times, Bloomberg were already
# on Google News. Economist moved to the section-level feed (403 on top-level).
SOURCES = [
    {"name": "BBC News",        "url": "http://feeds.bbci.co.uk/news/rss.xml",                                                          "colour": "#BB1919", "domain": "bbc.co.uk",         "text": "#fff"},
    {"name": "Reuters",         "url": "https://news.google.com/rss/search?q=reuters+news&hl=en-GB&gl=GB&ceid=GB:en",                   "colour": "#FF8000", "domain": "reuters.com",        "text": "#fff"},
    {"name": "Sky News",        "url": "https://feeds.skynews.com/feeds/rss/home.xml",                                                  "colour": "#003082", "domain": "skynews.com",        "text": "#fff"},
    {"name": "CNBC",            "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",                                         "colour": "#0070C8", "domain": "cnbc.com",           "text": "#fff"},
    {"name": "AP News",         "url": "https://news.google.com/rss/search?q=AP+associated+press+news&hl=en-GB&gl=GB&ceid=GB:en",      "colour": "#333333", "domain": "apnews.com",         "text": "#fff"},
    {"name": "CityAM",          "url": "https://news.google.com/rss/search?q=cityam+city+am&hl=en-GB&gl=GB&ceid=GB:en",                "colour": "#2E7D32", "domain": "cityam.com",         "text": "#fff"},
    {"name": "Gulf News",       "url": "https://news.google.com/rss/search?q=gulf+news+uae&hl=en-GB&gl=GB&ceid=GB:en",                 "colour": "#00796B", "domain": "gulfnews.com",       "text": "#fff"},
    {"name": "Khaleej Times",   "url": "https://news.google.com/rss/search?q=khaleej+times+UAE&hl=en-GB&gl=GB&ceid=GB:en",             "colour": "#6A1B9A", "domain": "khaleejtimes.com",   "text": "#fff"},
    {"name": "NDTV",            "url": "https://feeds.feedburner.com/ndtvnews-top-stories",                                             "colour": "#8B0000", "domain": "ndtv.com",           "text": "#fff"},
    {"name": "CNN",             "url": "http://rss.cnn.com/rss/edition.rss",                                                           "colour": "#CC0000", "domain": "cnn.com",            "text": "#fff"},
    {"name": "Forbes",          "url": "https://www.forbes.com/innovation/feed/",                                                       "colour": "#1B5E20", "domain": "forbes.com",         "text": "#fff"},
    {"name": "Financial Times", "url": "https://www.ft.com/rss/home",                                                                  "colour": "#D6580A", "domain": "ft.com",             "text": "#fff"},
    {"name": "Telegraph",       "url": "https://news.google.com/rss/search?q=daily+telegraph+UK+news&hl=en-GB&gl=GB&ceid=GB:en",       "colour": "#1C3F6E", "domain": "telegraph.co.uk",    "text": "#fff"},
    {"name": "The Times",       "url": "https://news.google.com/rss/search?q=the+times+uk+news&hl=en-GB&gl=GB&ceid=GB:en",            "colour": "#C41E3A", "domain": "thetimes.co.uk",     "text": "#fff"},
    {"name": "Bloomberg",       "url": "https://news.google.com/rss/search?q=bloomberg+finance&hl=en-GB&gl=GB&ceid=GB:en",            "colour": "#444444", "domain": "bloomberg.com",      "text": "#fff"},
    {"name": "The Economist",   "url": "https://www.economist.com/finance-and-economics/rss.xml",                                      "colour": "#E3120B", "domain": "economist.com",      "text": "#fff"},
]

ALL_SOURCE_NAMES = [s["name"] for s in SOURCES]
CATEGORIES = ["All Topics", "World News", "Business / Finance", "Technology", "Politics"]

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

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
FETCH_HEADERS = {"User-Agent": BROWSER_UA}


# ── Session state ──────────────────────────────────────────────────────────────

def _init_state():
    if "sources_selected" not in st.session_state:
        st.session_state.sources_selected = set(ALL_SOURCE_NAMES)
    if "filter_category" not in st.session_state:
        st.session_state.filter_category = "All Topics"
    if "filter_search" not in st.session_state:
        st.session_state.filter_search = ""
    for name in ALL_SOURCE_NAMES:
        if f"sb_ck_{name}" not in st.session_state:
            st.session_state[f"sb_ck_{name}"] = True
        if f"exp_ck_{name}" not in st.session_state:
            st.session_state[f"exp_ck_{name}"] = True
    for key, default in [
        ("sb_cat", "All Topics"), ("exp_cat", "All Topics"),
        ("sb_search", ""),        ("exp_search", ""),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


def _select_all():
    st.session_state.sources_selected = set(ALL_SOURCE_NAMES)
    for name in ALL_SOURCE_NAMES:
        st.session_state[f"sb_ck_{name}"]  = True
        st.session_state[f"exp_ck_{name}"] = True


def _deselect_all():
    st.session_state.sources_selected = set()
    for name in ALL_SOURCE_NAMES:
        st.session_state[f"sb_ck_{name}"]  = False
        st.session_state[f"exp_ck_{name}"] = False


def _on_sb_source(name):
    val = st.session_state[f"sb_ck_{name}"]
    if val: st.session_state.sources_selected.add(name)
    else:   st.session_state.sources_selected.discard(name)
    st.session_state[f"exp_ck_{name}"] = val


def _on_exp_source(name):
    val = st.session_state[f"exp_ck_{name}"]
    if val: st.session_state.sources_selected.add(name)
    else:   st.session_state.sources_selected.discard(name)
    st.session_state[f"sb_ck_{name}"] = val


def _on_sb_cat():
    st.session_state.filter_category = st.session_state.sb_cat
    st.session_state.exp_cat = st.session_state.sb_cat


def _on_exp_cat():
    st.session_state.filter_category = st.session_state.exp_cat
    st.session_state.sb_cat = st.session_state.exp_cat


def _on_sb_search():
    st.session_state.filter_search = st.session_state.sb_search
    st.session_state.exp_search = st.session_state.sb_search


def _on_exp_search():
    st.session_state.filter_search = st.session_state.exp_search
    st.session_state.sb_search = st.session_state.exp_search


# ── CSS injection ──────────────────────────────────────────────────────────────

def inject_css():
    st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">

<style>
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* Grain texture */
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

/* ── Status dots ── */
.source-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 2px 0;
    font-size: 13px;
}
.dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dot-live { background: #22c55e; box-shadow: 0 0 4px #22c55e88; }
.dot-fail { background: #ef4444; box-shadow: 0 0 4px #ef444488; }

/* ── Header ── */
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

/* ── Mobile filter expander ── */
[data-testid="stExpander"] {
    border: 1px solid #e8e8e8 !important;
    border-radius: 8px !important;
    background: #fafafa !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #555555 !important;
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
    flex-wrap: wrap;
}
.stats-count { font-size: 20px; font-weight: 700; color: #1a1a1a; }
.stats-sep   { color: #cccccc; }

/* ── Card grid — responsive ── */
.card-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    padding-bottom: 60px;
}
@media (max-width: 1100px) { .card-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 660px)  { .card-grid { grid-template-columns: 1fr; } }

/* ── Article card ── */
.news-card {
    background: #ffffff;
    border-radius: 10px;
    border: 1px solid #e8e8e8;
    border-left-width: 3px;
    padding: 18px 20px 16px 20px;
    transition: background 0.18s, box-shadow 0.18s;
    display: flex;
    flex-direction: column;
    gap: 9px;
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
    font-size: 15px;
    font-weight: 600;
    line-height: 1.4;
    color: #1a1a1a;
}
.card-title a {
    color: #1a1a1a !important;
    text-decoration: none !important;
}
.card-title a:hover { color: #000 !important; text-decoration: underline !important; }
.card-desc {
    font-size: 13px;
    color: #888888;
    line-height: 1.55;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    flex: 1;
}
.card-footer {
    font-size: 12px;
    color: #bbbbbb;
    margin-top: 2px;
}

/* ── Widget overrides ── */
[data-testid="stCheckbox"] label span { font-size: 13px !important; color: #555555 !important; }
.stSelectbox label, .stTextInput label { color: #888888 !important; font-size: 12px !important; }
div[data-testid="stSelectbox"] > div  { background: #f5f5f5 !important; border: 1px solid #e0e0e0 !important; border-radius: 6px !important; }
div[data-testid="stTextInput"] input  { background: #f5f5f5 !important; border: 1px solid #e0e0e0 !important; border-radius: 6px !important; color: #1a1a1a !important; font-size: 13px !important; }
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
.stButton button:hover { background: #ebebeb !important; border-color: #cccccc !important; color: #333333 !important; }
[data-testid="stToggle"] label { color: #555555 !important; font-size: 13px !important; }
#MainMenu, footer, header { visibility: hidden; }

/* ── No results ── */
.no-results { text-align: center; padding: 80px 20px; color: #bbbbbb; font-size: 14px; }
.no-results-icon { font-size: 48px; display: block; margin-bottom: 12px; opacity: 0.4; }

/* ── Checkbox / label legibility (mobile-safe) ── */
.stCheckbox label,
.stCheckbox label p,
.stCheckbox span,
[data-testid="stCheckbox"] label,
[data-testid="stCheckbox"] label p,
[data-testid="stCheckbox"] span {
    color: #1a1a1a !important;
    font-size: 14px !important;
    font-weight: 400 !important;
}
.stMultiSelect label,
.stSelectbox label,
[data-testid="stWidgetLabel"] p {
    color: #1a1a1a !important;
    font-size: 14px !important;
}
.streamlit-expanderHeader,
.streamlit-expanderHeader p {
    color: #1a1a1a !important;
    font-size: 15px !important;
    font-weight: 600 !important;
}
.streamlit-expanderContent label,
.streamlit-expanderContent p,
.streamlit-expanderContent span {
    color: #1a1a1a !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f5f5f5; }
::-webkit-scrollbar-thumb { background: #d0d0d0; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #bbbbbb; }
</style>
""", unsafe_allow_html=True)

    # Clock tick script — components.html is used because st.markdown strips <script> tags.
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


def truncate(text: str, chars: int = 200) -> str:
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
        resp = requests.get(source["url"], headers=FETCH_HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        articles = []
        for entry in feed.entries[:30]:
            title = getattr(entry, "title", "").strip()
            if not title:
                continue
            link = getattr(entry, "link", "") or ""
            desc = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
            articles.append({
                "source":             name,
                "title":              title,
                "url":                link,
                "description":        truncate(desc),
                "published_datetime": parse_datetime(entry),
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
    # Cap at 8 workers — bursting 16 concurrent Google News requests triggers throttling
    with ThreadPoolExecutor(max_workers=8) as ex:
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


# ── Static fragments ───────────────────────────────────────────────────────────

CLOCK_DIV = '<div id="mb-clock" class="header-clock">--:--:--</div>'

NEWSPAPER_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36" fill="none"
     stroke="#999" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/>
  <path d="M18 14h-8M15 18h-5M10 6h8v4h-8z"/>
</svg>
"""


# ── Shared filter widget renderers ────────────────────────────────────────────

def _render_source_controls(prefix: str, status: dict):
    """Select All / Deselect All buttons + checkboxes for a given key prefix."""
    c1, c2 = st.columns(2)
    c1.button("✅ Select All",   key=f"{prefix}_btn_all",  on_click=_select_all,   use_container_width=True)
    c2.button("❌ Deselect All", key=f"{prefix}_btn_none", on_click=_deselect_all, use_container_width=True)
    on_change = _on_sb_source if prefix == "sb" else _on_exp_source
    for src in SOURCES:
        name = src["name"]
        dot_cls = "dot-live" if status.get(name, False) else "dot-fail"
        st.checkbox(name, key=f"{prefix}_ck_{name}", on_change=on_change, args=(name,))
        st.markdown(
            f"<div class='source-item' style='margin-top:-28px;pointer-events:none'>"
            f"<span class='dot {dot_cls}'></span></div>",
            unsafe_allow_html=True,
        )


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar(status: dict):
    with st.sidebar:
        st.markdown(NEWSPAPER_SVG, unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:20px;font-weight:800;color:#1a1a1a;letter-spacing:-0.5px;margin:8px 0 4px 0'>The Nilesh Times</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='font-size:10px;color:#aaaaaa;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px'>The more you do, the more you can do.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<hr style='border-color:#e8e8e8;margin:4px 0 0 0'>", unsafe_allow_html=True)

        st.markdown("<div class='sidebar-section-header'>Refresh</div>", unsafe_allow_html=True)
        st.toggle("Auto-refresh (5 min)", value=True, key="auto_refresh_toggle")
        if st.button("🔄 Refresh Now", key="sb_refresh", type="secondary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("<div class='sidebar-section-header'>Sources</div>", unsafe_allow_html=True)
        _render_source_controls("sb", status)

        st.markdown("<div class='sidebar-section-header'>Category</div>", unsafe_allow_html=True)
        st.selectbox("Category", CATEGORIES, key="sb_cat",
                     label_visibility="collapsed", on_change=_on_sb_cat)

        st.markdown("<div class='sidebar-section-header'>Search</div>", unsafe_allow_html=True)
        st.text_input("Search headlines…", placeholder="Search headlines…", key="sb_search",
                      label_visibility="collapsed", on_change=_on_sb_search)


# ── Mobile filter expander ────────────────────────────────────────────────────

def render_mobile_expander(status: dict):
    sel_count = len(st.session_state.sources_selected)
    active = []
    if sel_count < len(SOURCES):
        active.append(f"{sel_count}/{len(SOURCES)} sources")
    if st.session_state.filter_category != "All Topics":
        active.append(st.session_state.filter_category)
    if st.session_state.filter_search:
        active.append(f'"{st.session_state.filter_search}"')
    label = "🔍 Filter & Search" + (f"  ·  {', '.join(active)}" if active else "")

    with st.expander(label, expanded=False):
        if st.button("🔄 Refresh Now", key="exp_refresh", type="secondary"):
            st.cache_data.clear()
            st.rerun()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<div class='sidebar-section-header' style='margin-top:4px'>Sources</div>",
                        unsafe_allow_html=True)
            _render_source_controls("exp", status)
        with col2:
            st.markdown("<div class='sidebar-section-header' style='margin-top:4px'>Category</div>",
                        unsafe_allow_html=True)
            st.selectbox("Category", CATEGORIES, key="exp_cat",
                         label_visibility="collapsed", on_change=_on_exp_cat)
            st.markdown("<div class='sidebar-section-header'>Search</div>", unsafe_allow_html=True)
            st.text_input("Search headlines…", placeholder="Search headlines…", key="exp_search",
                          label_visibility="collapsed", on_change=_on_exp_search)


# ── Card renderer ─────────────────────────────────────────────────────────────

def card_html(article: dict) -> str:
    colour     = article["colour"]
    txt_colour = article["text_colour"]
    source     = article["source"]
    title      = article["title"].replace('"', "&quot;").replace("<", "&lt;")
    url        = article["url"]
    desc       = article["description"].replace("<", "&lt;").replace(">", "&gt;")
    favicon    = article["favicon_url"]
    ago        = time_ago(article["published_datetime"])
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
    # Set at the very top, before inject_css / cache calls, so it always
    # reflects the true current render time, never the cache population time.
    page_rendered_at = datetime.utcnow().strftime("%H:%M:%S") + " UTC"

    inject_css()
    _init_state()

    if AUTOREFRESH_AVAILABLE and st.session_state.get("auto_refresh_toggle", True):
        st_autorefresh(interval=300_000, key="autorefresh_counter")

    with st.spinner("Fetching latest headlines…"):
        articles, status = fetch_all_feeds()

    render_sidebar(status)

    # ── Header ──
    st.markdown(f"""
<div class="morning-header">
  <div style="display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px">
    <div>
      <div class="morning-title">The Nilesh Times</div>
      <div class="morning-subtitle">The more you do, the more you can do.</div>
    </div>
    <div style="text-align:right">
      {CLOCK_DIV}
      <div style="font-size:11px;color:#aaaaaa;margin-top:4px">Last updated {page_rendered_at}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Mobile filter expander ──
    render_mobile_expander(status)

    # ── Read canonical filter state ──
    selected_sources = st.session_state.sources_selected
    category         = st.session_state.filter_category
    search           = st.session_state.filter_search

    # ── Filter ──
    filtered = [a for a in articles if a["source"] in selected_sources]
    if category != "All Topics":
        filtered = [a for a in filtered if infer_category(a["title"], a["description"]) == category]
    if search:
        q = search.lower()
        filtered = [a for a in filtered if q in a["title"].lower() or q in a["description"].lower()]

    live_sources = sum(1 for v in status.values() if v)
    total = len(filtered)

    # ── Stats bar ──
    filter_tag = (
        f"<span class='stats-sep'>·</span><span style='color:#999'>filtered: {category}</span>"
        if category != "All Topics" else ""
    )
    search_tag = (
        f"<span class='stats-sep'>·</span><span style='color:#999'>&ldquo;{search}&rdquo;</span>"
        if search else ""
    )
    stats_col, btn_col = st.columns([6, 1])
    with stats_col:
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
    with btn_col:
        st.markdown("<div style='padding-top:14px'>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Now", key="main_refresh", type="secondary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Card grid ──
    if not filtered:
        st.markdown("""
<div class="no-results">
  <span class="no-results-icon">📭</span>
  No headlines match your filters.
</div>
""", unsafe_allow_html=True)
        return

    grid_cards = [card_html(a) for a in filtered]
    st.markdown(f'<div class="card-grid">{"".join(grid_cards)}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
