
"""
Cascade Equity Perp Listing Tracker
"""

from datetime import datetime
import threading
import time
import pandas as pd
import streamlit as st

import db
import fetcher

st.set_page_config(
    page_title="Cascade | Listing Tracker",
    layout="wide",
    initial_sidebar_state="expanded",
)

LOCAL_DEV = getattr(fetcher, "LOCAL_DEV", False)

CURRENT_CASCADE_MARKETS = {
    "TSLA", "CRCL", "HOOD", "AMD", "PLTR", "COIN", "NVDA", "GOOGL", "META", "TSM",
}

THEME_RULES = [
    ("AI / Model Infra", ["artificial intelligence", " ai ", "machine learning", "foundation model", "model", "gpu", "accelerator", "data center", "cloud platform"]),
    ("Quantum", ["quantum", "qubit"]),
    ("Crypto / Exchange", ["crypto", "cryptocurrency", "digital asset", "exchange", "wallet", "blockchain", "stablecoin"]),
    ("Broker / Fintech", ["broker", "brokerage", "trading platform", "payments", "consumer finance", "fintech", "digital payments"]),
    ("Bank", ["bank", "commercial banking", "investment banking", "asset management", "consumer banking", "wealth management"]),
    ("Insurance / Managed Care", ["insurance", "managed care", "health benefits", "medical benefits"]),
    ("Healthcare Services", ["healthcare services", "care delivery", "pharmacy benefit", "medical services"]),
    ("Biotech / Pharma", ["biotech", "therapeutic", "pharmaceutical", "drug", "obesity", "glp-1", "clinical", "oncology"]),
    ("Medical Devices", ["medical device", "diagnostic", "surgical", "orthopedic", "cardiovascular device"]),
    ("Semis / Compute", ["semiconductor", "chip", "fab", "processor", "memory", "analog", "microcontroller", "graphics"]),
    ("Cloud / Enterprise Software", ["software", "cloud", "saas", "workflow", "enterprise", "developer", "productivity"]),
    ("Consumer Internet / Ads", ["social", "media", "advertising", "marketplace", "e-commerce", "consumer internet", "streaming", "search"]),
    ("EV / Autonomy", ["electric vehicle", " ev ", "autonomous", "autonomy", "robotaxi", "battery"]),
    ("Space / Defense", ["space", "satellite", "defense", "missile", "aerospace", "launch"]),
    ("Cybersecurity", ["security", "cyber", "identity", "threat", "endpoint", "firewall"]),
    ("Robotics / Industrial Automation", ["robot", "automation", "factory", "industrial software", "motion control"]),
    ("Energy / Power", ["energy", "oil", "gas", "utility", "power", "grid", "solar", "nuclear"]),
    ("Oil & Gas", ["oil", "gas", "upstream", "downstream", "refining", "exploration", "production"]),
    ("Telecom", ["telecom", "wireless", "broadband", "communications network"]),
    ("Consumer Finance", ["consumer finance", "credit card", "payments network"]),
]

SECTOR_FALLBACKS = {
    "Information Technology": "Technology",
    "Financials": "Financials",
    "Health Care": "Healthcare",
    "Industrials": "Industrials",
    "Energy": "Energy",
    "Communication Services": "Communications",
    "Consumer Discretionary": "Consumer Discretionary",
    "Consumer Staples": "Consumer Staples",
    "Utilities": "Utilities",
    "Materials": "Materials",
    "Real Estate": "Real Estate",
}

SUBINDUSTRY_FALLBACKS = {
    "Technology Hardware, Storage & Peripherals": "Hardware / Devices",
    "Systems Software": "Software",
    "Application Software": "Software",
    "Semiconductors": "Semis / Compute",
    "Semiconductor Materials & Equipment": "Semis / Compute",
    "Internet Services & Infrastructure": "Internet Infrastructure",
    "Interactive Media & Services": "Consumer Internet / Ads",
    "Integrated Telecommunication Services": "Telecom",
    "Wireless Telecommunication Services": "Telecom",
    "Health Care Equipment": "Medical Devices",
    "Health Care Supplies": "Medical Devices",
    "Health Care Distributors": "Healthcare Distribution",
    "Managed Health Care": "Insurance / Managed Care",
    "Pharmaceuticals": "Biotech / Pharma",
    "Biotechnology": "Biotech / Pharma",
    "Life Sciences Tools & Services": "Life Sciences Tools",
    "Diversified Banks": "Bank",
    "Regional Banks": "Bank",
    "Investment Banking & Brokerage": "Broker / Fintech",
    "Consumer Finance": "Consumer Finance",
    "Asset Management & Custody Banks": "Asset Management",
    "Property & Casualty Insurance": "Insurance",
    "Multi-line Insurance": "Insurance",
    "Oil & Gas Exploration & Production": "Oil & Gas",
    "Integrated Oil & Gas": "Oil & Gas",
    "Electric Utilities": "Utilities",
    "Aerospace & Defense": "Space / Defense",
    "Industrial Machinery & Supplies & Components": "Industrial Machinery",
    "Rail Transportation": "Transportation",
    "Air Freight & Logistics": "Logistics",
    "Hotels, Resorts & Cruise Lines": "Travel / Leisure",
    "Restaurants": "Restaurants",
    "Soft Drinks & Non-alcoholic Beverages": "Beverages",
    "Packaged Foods & Meats": "Packaged Foods",
    "Drug Retail": "Drug Retail",
    "Automobile Manufacturers": "Autos",
}

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, .stApp, .block-container, .stMarkdown, .stText, .stTextInput, .stSelectbox, .stMultiSelect, .stNumberInput, .stButton, .stDataFrame, .stDataEditor {
        font-family: Inter, -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", "Helvetica Neue", Arial, sans-serif !important;
    }

    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    div[data-testid="stSidebarHeader"],
    button[kind="header"],
    button[aria-label*="sidebar"],
    button[title*="sidebar"] {
        display: none !important;
    }

    [data-testid="stAppViewContainer"] > .main {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }

    /* ── Core dark theme ── */
    .stApp {
        background: #0d0d0d;
        color: #e8e8e8;
    }

    .block-container {
        max-width: 1600px;
        padding-top: 0.6rem;
        padding-bottom: 0.75rem;
        padding-left: 0.95rem;
        padding-right: 0.95rem;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: #111111;
        border-right: 1px solid #232323;
        min-width: 280px !important;
        max-width: 280px !important;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 0.6rem;
        padding-bottom: 0.6rem;
        padding-left: 0.85rem;
        padding-right: 0.85rem;
    }

    section[data-testid="stSidebar"] *,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div {
        color: #e8e8e8 !important;
    }

    /* Remove the extra category gaps — st.divider() renders as <hr> inside stMarkdown */
    section[data-testid="stSidebar"] hr {
        display: none !important;
        margin: 0 !important;
        padding: 0 !important;
        height: 0 !important;
    }

    /* Collapse the element container wrapping the divider's <hr> */
    section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(hr),
    section[data-testid="stSidebar"] [data-testid="stMarkdown"]:has(hr),
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(hr) {
        display: none !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }

    section[data-testid="stSidebar"] [data-testid="stElementContainer"] {
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
    }

    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #666666 !important;
        line-height: 1.15;
        margin-top: 0.6rem !important;
        margin-bottom: 0.12rem !important;
    }

    /* ── Button ── */
    div[data-testid="stButton"] button {
        border-radius: 999px !important;
        border: 1px solid #333333 !important;
        background: #1e1e1e !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        box-shadow: none !important;
        min-height: 2.5rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
    }

    div[data-testid="stButton"] button *,
    div[data-testid="stButton"] button p,
    div[data-testid="stButton"] button span {
        color: #ffffff !important;
        fill: #ffffff !important;
    }

    div[data-testid="stButton"] button:hover,
    div[data-testid="stButton"] button:focus,
    div[data-testid="stButton"] button:active {
        background: #2a2a2a !important;
        border-color: #444444 !important;
        color: #ffffff !important;
        box-shadow: none !important;
    }

    div[data-testid="stButton"] button:hover *,
    div[data-testid="stButton"] button:focus *,
    div[data-testid="stButton"] button:active * {
        color: #ffffff !important;
    }

    /* ── Sidebar sliders ── */
    section[data-testid="stSidebar"] [data-baseweb="slider"] {
        padding-top: 0.01rem !important;
        padding-bottom: 0.01rem !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }

    section[data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"] {
        background: #ffffff !important;
        border-color: #ffffff !important;
        box-shadow: none !important;
    }

    section[data-testid="stSidebar"] [data-baseweb="slider"] > div > div > div {
        background: #333333 !important;
    }

    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
        margin-bottom: 0.02rem !important;
    }

    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        line-height: 1.15 !important;
        color: #aaaaaa !important;
        margin-bottom: 0 !important;
    }

    /* ── Hero / page header ── */
    .hero {
        background: transparent;
        border: none;
        border-bottom: 1px solid #1e1e1e;
        border-radius: 0;
        padding: 18px 4px 16px 4px;
        margin-bottom: 16px;
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
    }

    .hero-left {}

    .hero-eyebrow {
        font-size: 0.72rem;
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #666666;
        margin-bottom: 4px;
    }

    .hero-title {
        font-size: 2.1rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.04em;
        line-height: 1.0;
        margin: 0;
    }

    .hero-right {
        font-size: 0.75rem;
        color: #555555;
        text-align: right;
        padding-bottom: 4px;
    }

    .hero-subtitle {
        color: #666666;
        font-size: 0.82rem;
        margin-top: 5px;
    }

    /* ── Metric cards ── */
    .metric-wrap {
        background: #111111;
        border: 1px solid #1e1e1e;
        border-radius: 12px;
        padding: 12px 14px 10px 14px;
        min-height: 74px;
    }

    .metric-label {
        color: #555555;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.07em;
        text-transform: uppercase;
        margin-bottom: 5px;
    }

    .metric-num {
        color: #ffffff;
        font-size: 1.5rem;
        font-weight: 700;
        line-height: 1.0;
        letter-spacing: -0.04em;
    }

    .metric-sub {
        color: #555555;
        font-size: 0.72rem;
        margin-top: 3px;
    }

    /* ── Info panels ── */
    .panel, .legend {
        background: #111111;
        border: 1px solid #1e1e1e;
        border-radius: 12px;
        padding: 12px 14px;
        margin-top: 8px;
    }

    .panel h3, .legend h3 {
        margin-top: 0;
        margin-bottom: 5px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.07em;
        text-transform: uppercase;
        color: #666666;
    }

    .panel p, .legend p, .legend li {
        color: #888888;
        font-size: 0.82rem;
        line-height: 1.5;
        margin: 0;
    }

    /* ── Expander ── */
    [data-testid="stExpander"] {
        border: 1px solid #1e1e1e !important;
        background: #111111 !important;
        border-radius: 12px !important;
        margin-top: 8px !important;
    }

    [data-testid="stExpander"] summary {
        list-style: none !important;
        cursor: pointer;
    }

    [data-testid="stExpander"] summary p {
        color: #888888 !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
    }

    [data-testid="stExpander"] .stMarkdown p,
    [data-testid="stExpander"] .stMarkdown li {
        color: #888888 !important;
        font-size: 0.82rem !important;
    }

    /* ── Data table ── */
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #1e1e1e;
        background: #111111;
    }

    /* ── Divider ── */
    hr {
        border-color: #1e1e1e !important;
    }

    /* ── Footer ── */
    .footer-note {
        color: #444444;
        font-size: 0.72rem;
        text-align: center;
        margin-top: 6px;
    }

    /* ── Narrative filter label ── */
    .narrative-label {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.07em;
        text-transform: uppercase;
        color: #666666;
        margin-top: 0.05rem;
        margin-bottom: 0.22rem;
    }

    /* ── Loading box ── */
    .loading-box {
        background: #111111;
        border: 1px solid #1e1e1e;
        border-radius: 12px;
        padding: 14px 16px;
        color: #888888;
        font-size: 0.88rem;
    }

    /* ── Dropdowns / multiselect ── */
    div[data-baseweb="select"] > div {
        min-height: 40px !important;
        border-radius: 10px !important;
        border: 1px solid #232323 !important;
        background: #161616 !important;
        box-shadow: none !important;
        padding-top: 2px !important;
        padding-bottom: 2px !important;
    }

    div[data-baseweb="select"] input {
        color: #cccccc !important;
        font-size: 0.88rem !important;
    }

    div[data-baseweb="select"] input::placeholder {
        color: #555555 !important;
    }

    div[data-baseweb="select"] span,
    div[data-baseweb="select"] svg {
        color: #666666 !important;
        fill: #666666 !important;
    }

    div[data-baseweb="tag"] {
        border-radius: 999px !important;
        background: #1e1e1e !important;
        color: #cccccc !important;
        border: 1px solid #333333 !important;
        padding: 2px 8px !important;
    }

    div[data-baseweb="tag"] * {
        color: #cccccc !important;
        fill: #cccccc !important;
    }

    [role="listbox"] {
        border-radius: 10px !important;
        border: 1px solid #232323 !important;
        background: #161616 !important;
    }

    [role="option"] {
        color: #cccccc !important;
        background: #161616 !important;
    }

    [role="option"]:hover {
        background: #1e1e1e !important;
    }

    /* ── Toggle ── */
    [data-testid="stToggle"] span[data-checked="true"] {
        background: #ffffff !important;
    }

    /* ── Responsive ── */
    @media (max-width: 1440px) {
        .block-container {
            padding-left: 0.85rem;
            padding-right: 0.85rem;
        }
        section[data-testid="stSidebar"] {
            min-width: 255px !important;
            max-width: 255px !important;
        }
        .hero-title {
            font-size: 1.8rem;
        }
    }

    @media (max-width: 1280px) {
        .metric-num {
            font-size: 1.3rem;
        }
        .hero-title {
            font-size: 1.6rem;
        }
        section[data-testid="stSidebar"] {
            min-width: 235px !important;
            max-width: 235px !important;
        }
    }

    /* ── Sidebar slider typography ── */
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] label,
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] span {
        margin-bottom: 7px !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSliderThumbValue"],
    section[data-testid="stSidebar"] [data-testid="stSliderThumbValue"] *,
    section[data-testid="stSidebar"] [data-testid="stSliderThumbValue"] p,
    section[data-testid="stSidebar"] [data-testid="stSliderThumbValue"] span {
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        line-height: 1.1 !important;
        color: #cccccc !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSliderTickBar"],
    section[data-testid="stSidebar"] [data-testid="stSliderTickBar"] *,
    section[data-testid="stSidebar"] [data-testid="stSliderTickBar"] p,
    section[data-testid="stSidebar"] [data-testid="stSliderTickBar"] span {
        font-size: 0.68rem !important;
        font-weight: 400 !important;
        line-height: 1.1 !important;
        color: #555555 !important;
    }

</style>
""",
    unsafe_allow_html=True,
)

for key, default in {
    "data": None,
    "last_refresh": None,
    "save_status": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


@st.cache_data(ttl=3600, show_spinner=False)
def load_market_data(force_live=False):
    return fetcher.run_screen(force_live=force_live)


def load_market_data_with_animation(force_live=False, local_mode=False):
    result = {}
    error = {}

    def worker():
        try:
            result["data"] = load_market_data(force_live=force_live)
        except Exception as exc:
            error["exc"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    placeholder = st.empty()
    messages = [
        "Loading data. Please wait.",
        "Loading data. Please wait..",
        "Loading data. Please wait...",
    ]
    if local_mode and not force_live:
        messages = [
            "Loading data. Please wait.",
            "Loading data. Please wait..",
            "Loading data. Please wait...",
        ]

    i = 0
    while thread.is_alive():
        placeholder.markdown(
            f"<div class='loading-box'>{messages[i % len(messages)]}</div>",
            unsafe_allow_html=True,
        )
        time.sleep(0.4)
        i += 1

    thread.join()
    placeholder.empty()

    if "exc" in error:
        raise error["exc"]
    return result["data"]


def classify_theme(company: str, sector: str, sub_industry: str, summary: str, profile_sector: str = "", profile_industry: str = "") -> str:
    text = f" {company} {sector} {sub_industry} {profile_sector} {profile_industry} {summary} ".lower()
    for label, keywords in THEME_RULES:
        if any(keyword in text for keyword in keywords):
            return label
    if profile_industry in SUBINDUSTRY_FALLBACKS:
        return SUBINDUSTRY_FALLBACKS[profile_industry]
    if sub_industry in SUBINDUSTRY_FALLBACKS:
        return SUBINDUSTRY_FALLBACKS[sub_industry]
    if profile_sector in SECTOR_FALLBACKS:
        return SECTOR_FALLBACKS[profile_sector]
    if sector in SECTOR_FALLBACKS:
        return SECTOR_FALLBACKS[sector]
    return profile_industry or sub_industry or profile_sector or sector or ""


@st.cache_data(ttl=3600, show_spinner=False)
def build_base_rows(df_market, meta, profiles):
    rows = []
    for _, row in df_market.iterrows():
        ticker = row["ticker"]
        profile = profiles.get(ticker) or {}

        meta_sector = meta.loc[ticker, "GICS Sector"] if ticker in meta.index else ""
        meta_sub_industry = meta.loc[ticker, "GICS Sub-Industry"] if ticker in meta.index and "GICS Sub-Industry" in meta.columns else ""

        profile_sector = profile.get("sector", "")
        profile_industry = profile.get("industry", "")

        meta_company = meta.loc[ticker, "Security"] if ticker in meta.index and "Security" in meta.columns else ""
        profile_company = profile.get("company_name", "")

        company = profile_company or meta_company or ticker
        summary = profile.get("summary", "")
        market_cap = profile.get("market_cap")

        theme = classify_theme(
            company=company,
            sector=meta_sector,
            sub_industry=meta_sub_industry,
            summary=summary,
            profile_sector=profile_sector,
            profile_industry=profile_industry,
        )

        rows.append(
            {
                "Bucket": "",
                "Ticker": f"https://finance.yahoo.com/quote/{ticker}",
                "Ticker Symbol": ticker,
                "Company": company,
                "Narrative": theme,
                "Business Summary": summary,
                "Mkt Cap ($B)": round(market_cap / 1e9, 1) if market_cap else None,
                "Today Vol ($M)": int(row["today_vol_m"]),
                "5D Avg Vol ($M)": int(row["avg_5d_vol_m"]),
                "20D Avg Vol ($M)": int(row["avg_20d_vol_m"]),
                "5D vs 20D %": row["build_pct"],
                "Today vs 5D %": row["heat_pct"],
                "Auto Score": row["auto_score"],
            }
        )
    return pd.DataFrame(rows)


def recommendation_from_score(score: float, list_now_min: float, monitor_min: float, watch_min: float) -> str:
    if score >= list_now_min:
        return "🟢 LIST NOW"
    if score >= monitor_min:
        return "🟡 MONITOR"
    if score >= watch_min:
        return "⚪ WATCH"
    return "⚫ SKIP"


def build_display_df(
    base_df,
    scores_db,
    min_vol,
    min_auto_score,
    near_cutoff_count,
    exclude_current,
    selected_narratives,
    vol_buffer,
    score_buffer,
    hl_gap_weight,
    momentum_weight,
    list_now_min,
    monitor_min,
    watch_min,
):
    if base_df.empty:
        return base_df

    working = base_df.copy()

    if exclude_current:
        working = working[~working["Ticker Symbol"].isin(CURRENT_CASCADE_MARKETS)]

    if selected_narratives and "All" not in selected_narratives:
        working = working[working["Narrative"].isin(selected_narratives)]

    qualified = working[
        (working["Today Vol ($M)"] >= min_vol) &
        (working["Auto Score"] >= min_auto_score)
    ].copy()
    qualified["Bucket"] = "Qualified"

    near_cutoff = working[
        (
            ((working["Today Vol ($M)"] < min_vol) & (working["Today Vol ($M)"] >= max(0, min_vol - vol_buffer))) |
            ((working["Auto Score"] < min_auto_score) & (working["Auto Score"] >= max(0, min_auto_score - score_buffer)))
        )
    ].copy()
    near_cutoff = near_cutoff[~near_cutoff["Ticker Symbol"].isin(qualified["Ticker Symbol"])]
    near_cutoff = near_cutoff.sort_values(["Today Vol ($M)", "Auto Score"], ascending=False).head(near_cutoff_count)
    near_cutoff["Bucket"] = "Near Cutoff"

    df = pd.concat([qualified, near_cutoff], ignore_index=True)
    if df.empty:
        return df

    hl_gap_vals, momentum_vals, notes_vals = [], [], []
    full_scores, recs, reasons = [], [], []

    for _, row in df.iterrows():
        ticker = row["Ticker Symbol"]
        manual = scores_db.get(ticker, {})

        hl_gap = manual.get("not_hl")
        momentum = manual.get("price_mom")
        notes = manual.get("notes", "")

        bonus = 0.0
        reason_parts = [f"Auto {float(row['Auto Score']):.1f}"]

        if hl_gap is not None:
            add = float(hl_gap) * hl_gap_weight
            bonus += add
            reason_parts.append(f"HL Gap +{add:.1f}")

        if momentum is not None:
            add = (float(momentum) / 5.0) * momentum_weight
            bonus += add
            reason_parts.append(f"Momentum +{add:.1f}")

        score = round(float(row["Auto Score"]) + bonus, 1)
        rec = recommendation_from_score(score, list_now_min, monitor_min, watch_min)

        hl_gap_vals.append(hl_gap)
        momentum_vals.append(momentum)
        notes_vals.append(notes)
        full_scores.append(score)
        recs.append(rec)
        reasons.append(" | ".join(reason_parts))

    df["HL Gap"] = hl_gap_vals
    df["Momentum"] = momentum_vals
    df["Full R/R"] = full_scores
    df["Recommendation"] = recs
    df["Why"] = reasons
    df["Notes"] = notes_vals

    order_cols = [
        "Bucket", "Ticker", "Company", "Narrative", "Mkt Cap ($B)",
        "Today Vol ($M)", "5D Avg Vol ($M)", "20D Avg Vol ($M)",
        "5D vs 20D %", "Today vs 5D %", "Auto Score",
        "HL Gap", "Momentum", "Full R/R", "Recommendation", "Why", "Notes", "Business Summary", "Ticker Symbol",
    ]
    df = df[order_cols]

    bucket_order = pd.Categorical(df["Bucket"], categories=["Qualified", "Near Cutoff"], ordered=True)
    df = df.assign(_bucket_order=bucket_order)
    df = df.sort_values(["_bucket_order", "Full R/R", "Today Vol ($M)"], ascending=[True, False, False]).drop(columns=["_bucket_order"])
    return df.reset_index(drop=True)


with st.sidebar:
    st.markdown("### Controls")
    if st.button("Refresh Data", width="stretch", help="Pull a fresh Yahoo Finance snapshot."):
        load_market_data.clear()
        build_base_rows.clear()
        st.session_state.data = None
        st.session_state.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.session_state.data = load_market_data_with_animation(force_live=True, local_mode=False)
        st.rerun()

    st.divider()
    st.markdown("### Screen")
    min_vol = st.slider("Min daily dollar volume ($M)", 100, 5000, 500, step=50)
    min_auto_score = st.slider("Min auto score", 0.0, 10.0, 3.0, step=0.5)
    near_cutoff_count = st.slider("Near-cutoff extras", 0, 30, 10, step=1)
    vol_buffer = st.slider("Near-cutoff volume window ($M)", 25, 500, 150, step=25)
    score_buffer = st.slider("Near-cutoff auto-score window", 0.5, 4.0, 1.0, step=0.5)
    exclude_current = st.toggle("Exclude live Cascade markets", value=True)

    st.divider()
    st.markdown("### Ranking weights")
    hl_gap_weight = st.slider("HL Gap weight", 0.0, 4.0, 1.5, step=0.5)
    momentum_weight = st.slider("Momentum weight", 0.0, 4.0, 1.5, step=0.5)

    st.divider()
    st.markdown("### Recommendation bands")
    list_now_min = st.slider("List Now minimum", 4.0, 12.0, 7.0, step=0.5)
    monitor_min = st.slider("Monitor minimum", 2.0, 10.0, 5.0, step=0.5)
    watch_min = st.slider("Watch minimum", 0.0, 8.0, 3.5, step=0.5)

    if monitor_min > list_now_min:
        monitor_min = list_now_min
    if watch_min > monitor_min:
        watch_min = monitor_min

    st.divider()
    st.markdown("### Recommendation filter")
    show_rec = st.multiselect(
        "Show recommendations",
        ["🟢 LIST NOW", "🟡 MONITOR", "⚪ WATCH", "⚫ SKIP"],
        default=["🟢 LIST NOW", "🟡 MONITOR", "⚪ WATCH", "⚫ SKIP"],
        label_visibility="collapsed",
        placeholder="Filter recommendations",
    )

refresh_ts = st.session_state.last_refresh or "Not yet loaded"
st.markdown(
    f"""
<div class="hero">
  <div class="hero-left">
    <div class="hero-eyebrow">Market overview</div>
    <div class="hero-title">S&amp;P 500 listing candidates</div>
    <div class="hero-subtitle">Equity perp screen for Cascade mainnet. Current markets excluded by default.</div>
  </div>
  <div class="hero-right">Refreshed {refresh_ts}</div>
</div>
""",
    unsafe_allow_html=True,
)

if st.session_state.data is None:
    df_market, meta, profiles = load_market_data_with_animation(force_live=False, local_mode=LOCAL_DEV)
    st.session_state.data = (df_market, meta, profiles)
    if st.session_state.last_refresh is None:
        st.session_state.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M")
else:
    df_market, meta, profiles = st.session_state.data

scores_db = db.load_scores()
base_df = build_base_rows(df_market, meta, profiles)

all_narratives = sorted([x for x in base_df["Narrative"].dropna().unique().tolist() if x]) if not base_df.empty else []

st.markdown("<div class='narrative-label'>Narrative filter</div>", unsafe_allow_html=True)
selected_narratives = st.multiselect(
    "Narrative filter",
    ["All"] + all_narratives,
    default=["All"],
    label_visibility="collapsed",
    placeholder="Enter a narrative here...",
)

if selected_narratives != ["All"] and "All" in selected_narratives:
    selected_narratives = [x for x in selected_narratives if x != "All"]

df_display = build_display_df(
    base_df=base_df,
    scores_db=scores_db,
    min_vol=min_vol,
    min_auto_score=min_auto_score,
    near_cutoff_count=near_cutoff_count,
    exclude_current=exclude_current,
    selected_narratives=selected_narratives or ["All"],
    vol_buffer=vol_buffer,
    score_buffer=score_buffer,
    hl_gap_weight=hl_gap_weight,
    momentum_weight=momentum_weight,
    list_now_min=list_now_min,
    monitor_min=monitor_min,
    watch_min=watch_min,
)

if show_rec and not df_display.empty:
    df_display = df_display[df_display["Recommendation"].isin(show_rec)]

qualifying_count = int((df_display["Bucket"] == "Qualified").sum()) if not df_display.empty else 0
near_count = int((df_display["Bucket"] == "Near Cutoff").sum()) if not df_display.empty else 0
list_now = int((df_display["Recommendation"] == "🟢 LIST NOW").sum()) if not df_display.empty else 0
unique_narratives = int(df_display["Narrative"].replace("", pd.NA).dropna().nunique()) if not df_display.empty else 0

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="metric-wrap"><div class="metric-label">Qualified names</div><div class="metric-num">{qualifying_count}</div><div class="metric-sub">meeting current cutoffs</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-wrap"><div class="metric-label">Near cutoff</div><div class="metric-num">{near_count}</div><div class="metric-sub">borderline names kept in view</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-wrap"><div class="metric-label">List now</div><div class="metric-num">{list_now}</div><div class="metric-sub">top current recommendations</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-wrap"><div class="metric-label">Narratives in view</div><div class="metric-num">{unique_narratives}</div><div class="metric-sub">industry tags in current results</div></div>', unsafe_allow_html=True)

st.markdown(
    """
<div class="panel">
  <h3>How the volume signal works</h3>
  <p><strong>5D vs 20D %</strong> measures whether volume has been building over the last week relative to the last month. <strong>Today vs 5D %</strong> measures whether today is hotter or cooler than that recent baseline. Auto Score combines liquidity, build, and heat. Manual inputs then layer on top.</p>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="legend">
  <h3>Legend</h3>
  <p><strong>HL Gap</strong> = whether the name is not on Hyperliquid yet (0 or 1).<br>
  <strong>Momentum</strong> = your manual 1 to 5 read on non-volume momentum.<br>
  <strong>Auto Score</strong> = liquidity + build + heat score from market data.<br>
  <strong>Full R/R</strong> = Auto Score + manual bonuses.</p>
</div>
""",
    unsafe_allow_html=True,
)

with st.expander("Definitions and formula details", expanded=False):
    st.markdown(
        f"""
- **Today Vol ($M)**: today's dollar volume in millions
- **5D Avg Vol ($M)**: average daily dollar volume over the last 5 trading days
- **20D Avg Vol ($M)**: average daily dollar volume over the last 20 trading days
- **5D vs 20D %**: `((5D Avg - 20D Avg) / 20D Avg) × 100`
- **Today vs 5D %**: `((Today Vol - 5D Avg) / 5D Avg) × 100`

**Manual bonus**
- `HL Gap × {hl_gap_weight:.1f}`
- `(Momentum / 5) × {momentum_weight:.1f}`

**Recommendation bands**
- `🟢 LIST NOW` at **{list_now_min:.1f}+**
- `🟡 MONITOR` at **{monitor_min:.1f}+**
- `⚪ WATCH` at **{watch_min:.1f}+**
- `⚫ SKIP` below **{watch_min:.1f}**
"""
    )

if df_display.empty:
    st.info("No stocks match your current settings. Lower the cutoffs or add more near-cutoff rows.")
else:
    col_config = {
        "Bucket": st.column_config.TextColumn("Bucket", width="small", disabled=True),
        "Ticker": st.column_config.LinkColumn("Ticker", width="small", display_text=r"https://finance\.yahoo\.com/quote/(.*)"),
        "Company": st.column_config.TextColumn("Company", width="medium", disabled=True),
        "Narrative": st.column_config.TextColumn("Narrative", width="medium", disabled=True, help="Derived from company description plus sector and industry metadata."),
        "Mkt Cap ($B)": st.column_config.NumberColumn("Mkt Cap ($B)", format="%.1f B", disabled=True),
        "Today Vol ($M)": st.column_config.NumberColumn("Today Vol ($M)", format="%,d", disabled=True, help="Today's dollar volume in millions."),
        "5D Avg Vol ($M)": st.column_config.NumberColumn("5D Avg Vol ($M)", format="%,d", disabled=True, help="Average daily dollar volume over the last 5 trading days."),
        "20D Avg Vol ($M)": st.column_config.NumberColumn("20D Avg Vol ($M)", format="%,d", disabled=True, help="Average daily dollar volume over the last 20 trading days."),
        "5D vs 20D %": st.column_config.NumberColumn("5D vs 20D %", format="%.1f%%", disabled=True, help="How much recent weekly volume is above or below the last 20-day baseline."),
        "Today vs 5D %": st.column_config.NumberColumn("Today vs 5D %", format="%.1f%%", disabled=True, help="How much today is above or below the recent 5-day baseline."),
        "Auto Score": st.column_config.NumberColumn("Auto Score", format="%.1f", disabled=True, help="Liquidity plus build plus heat."),
        "HL Gap": st.column_config.NumberColumn("HL Gap", min_value=0, max_value=1, step=1, help="1 if the name is not on Hyperliquid yet, otherwise 0."),
        "Momentum": st.column_config.NumberColumn("Momentum", min_value=1, max_value=5, step=1, help="Your manual momentum read from 1 to 5."),
        "Full R/R": st.column_config.NumberColumn("Full R/R", format="%.1f", disabled=True, help="Auto Score plus manual bonus."),
        "Recommendation": st.column_config.TextColumn("Recommendation", width="medium", disabled=True),
        "Why": st.column_config.TextColumn("Why", width="large", disabled=True, help="Breakdown of the current score."),
        "Notes": st.column_config.TextColumn("Notes", width="large"),
        "Business Summary": st.column_config.TextColumn("Business Summary", width="large", disabled=True),
        "Ticker Symbol": st.column_config.TextColumn("Ticker Symbol", disabled=True),
    }

    edited_df = st.data_editor(
        df_display,
        column_config=col_config,
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        key="main_table",
        column_order=[
            "Bucket", "Ticker", "Company", "Narrative", "Mkt Cap ($B)",
            "Today Vol ($M)", "5D Avg Vol ($M)", "20D Avg Vol ($M)",
            "5D vs 20D %", "Today vs 5D %", "Auto Score",
            "HL Gap", "Momentum", "Full R/R", "Recommendation", "Why", "Notes"
        ],
    )

    if not edited_df.empty:
        detail_vals, full_vals, rec_vals = [], [], []
        for _, row in edited_df.iterrows():
            bonus = 0.0
            parts = [f"Auto {float(row['Auto Score']):.1f}"]

            if pd.notna(row.get("HL Gap")):
                add = float(row["HL Gap"]) * hl_gap_weight
                bonus += add
                parts.append(f"HL Gap +{add:.1f}")

            if pd.notna(row.get("Momentum")):
                add = (float(row["Momentum"]) / 5.0) * momentum_weight
                bonus += add
                parts.append(f"Momentum +{add:.1f}")

            score = round(float(row["Auto Score"]) + bonus, 1)
            rec = recommendation_from_score(score, list_now_min, monitor_min, watch_min)

            full_vals.append(score)
            rec_vals.append(rec)
            detail_vals.append(" | ".join(parts))

        edited_df["Full R/R"] = full_vals
        edited_df["Recommendation"] = rec_vals
        edited_df["Why"] = detail_vals

    save_col, status_col = st.columns([1, 4])
    with save_col:
        save_clicked = st.button("Save scores", width="stretch")
    with status_col:
        if st.session_state.save_status:
            st.success(st.session_state.save_status)

    if save_clicked:
        new_scores = {}
        for _, row in edited_df.iterrows():
            ticker = row["Ticker Symbol"]
            entry = {}

            if pd.notna(row.get("HL Gap")):
                entry["not_hl"] = int(row["HL Gap"])
            if pd.notna(row.get("Momentum")):
                entry["price_mom"] = int(row["Momentum"])
            if row.get("Notes"):
                entry["notes"] = str(row["Notes"])

            if entry:
                new_scores[ticker] = entry

        with st.spinner("Saving to database..."):
            ok = db.save_scores(new_scores)

        if ok:
            st.session_state.save_status = f"Saved scores for {len(new_scores)} stocks at {datetime.now().strftime('%H:%M:%S')}"
        else:
            st.session_state.save_status = "Save failed. Check your Supabase credentials and stock_scores table."
        st.rerun()

st.divider()
st.markdown(
    "<div class='footer-note'>Data via yfinance. Manual scores stored in Supabase. Current Cascade market exclusions are editable in app.py via CURRENT_CASCADE_MARKETS.</div>",
    unsafe_allow_html=True,
)
