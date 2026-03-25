
"""
Cascade Equity Perp Listing Tracker
"""

from datetime import datetime
import pandas as pd
import streamlit as st

import db
import fetcher

st.set_page_config(
    page_title="Cascade | Listing Tracker",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    .stApp {
        background: #ffffff;
        color: #111111;
    }
    .block-container {
        padding-top: 0.85rem;
        padding-bottom: 1.6rem;
    }
    section[data-testid="stSidebar"] {
        background: #fafafa;
        border-right: 1px solid #e6e6e6;
    }
    section[data-testid="stSidebar"] * {
        color: #111111 !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"] {
        background: #111111 !important;
        border-color: #111111 !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="slider"] > div > div > div {
        background: #d8d8d8 !important;
    }
    div[data-testid="stButton"] button {
        border-radius: 999px;
        border: 1px solid #111111;
        background: #111111;
        color: #ffffff !important;
        font-weight: 600;
        box-shadow: none;
        min-height: 2.8rem;
    }
    div[data-testid="stButton"] button:hover {
        background: #222222;
        border-color: #222222;
        color: #ffffff !important;
    }
    .hero {
        background: #ffffff;
        border: 1px solid #dedede;
        border-radius: 18px;
        padding: 18px 22px 16px 22px;
        margin-bottom: 14px;
    }
    .hero-title {
        font-size: 1.9rem;
        font-weight: 700;
        color: #111111;
        letter-spacing: -0.04em;
        margin: 0;
    }
    .hero-subtitle {
        color: #5f5f5f;
        font-size: 0.92rem;
        margin-top: 6px;
    }
    .metric-wrap {
        background: #ffffff;
        border: 1px solid #dedede;
        border-radius: 16px;
        padding: 14px 16px 12px 16px;
        min-height: 96px;
    }
    .metric-label {
        color: #6a6a6a;
        font-size: 0.8rem;
        margin-bottom: 6px;
    }
    .metric-num {
        color: #111111;
        font-size: 1.65rem;
        font-weight: 700;
        line-height: 1.05;
        letter-spacing: -0.04em;
    }
    .metric-sub {
        color: #6a6a6a;
        font-size: 0.82rem;
        margin-top: 5px;
    }
    .panel, .legend {
        background: #ffffff;
        border: 1px solid #dedede;
        border-radius: 16px;
        padding: 14px 16px;
        margin-top: 10px;
    }
    .panel h3, .legend h3 {
        margin-top: 0;
        margin-bottom: 6px;
        font-size: 1.0rem;
        letter-spacing: -0.03em;
        color: #111111;
    }
    .panel p, .legend p, .legend li {
        color: #666666;
        font-size: 0.88rem;
        margin: 0;
    }
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid #dedede;
    }
    .footer-note {
        color: #777777;
        font-size: 0.77rem;
        text-align: center;
        margin-top: 8px;
    }
    .refresh-note {
        color: #666666;
        font-size: 0.80rem;
        margin-top: 0.35rem;
        margin-bottom: 0.15rem;
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
def load_market_data():
    return fetcher.run_screen()


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
                "Theme": theme,
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
    selected_themes,
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

    if selected_themes and "All" not in selected_themes:
        working = working[working["Theme"].isin(selected_themes)]

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
        "Bucket", "Ticker", "Company", "Theme", "Mkt Cap ($B)",
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
    if st.button("Refresh market data", use_container_width=True, help="Pull a fresh Yahoo Finance snapshot. Usually takes 1 to 2 minutes."):
        load_market_data.clear()
        build_base_rows.clear()
        st.session_state.data = None
        st.session_state.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.rerun()
    st.markdown("<div class='refresh-note'>Pulls a fresh market snapshot. Cached for 1 hour.</div>", unsafe_allow_html=True)

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
    )

refresh_ts = st.session_state.last_refresh or "Not yet loaded"
st.markdown(
    f"""
<div class="hero">
  <div class="hero-title">Markets</div>
  <div class="hero-subtitle">S&amp;P 500 screen for equity perp listing candidates. Current Cascade markets excluded by default. Last refresh: {refresh_ts}</div>
</div>
""",
    unsafe_allow_html=True,
)

if st.session_state.data is None:
    with st.spinner("Screening S&P 500 via Yahoo Finance. This usually takes around 2 minutes on a cold refresh."):
        df_market, meta, profiles = load_market_data()
    st.session_state.data = (df_market, meta, profiles)
    if st.session_state.last_refresh is None:
        st.session_state.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M")
else:
    df_market, meta, profiles = st.session_state.data

scores_db = db.load_scores()
base_df = build_base_rows(df_market, meta, profiles)

all_themes = sorted([x for x in base_df["Theme"].dropna().unique().tolist() if x]) if not base_df.empty else []
selected_themes = st.multiselect("Filter by theme", ["All"] + all_themes, default=["All"])
if selected_themes != ["All"] and "All" in selected_themes:
    selected_themes = [x for x in selected_themes if x != "All"]

df_display = build_display_df(
    base_df=base_df,
    scores_db=scores_db,
    min_vol=min_vol,
    min_auto_score=min_auto_score,
    near_cutoff_count=near_cutoff_count,
    exclude_current=exclude_current,
    selected_themes=selected_themes or ["All"],
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
unique_themes = int(df_display["Theme"].replace("", pd.NA).dropna().nunique()) if not df_display.empty else 0

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="metric-wrap"><div class="metric-label">Qualified names</div><div class="metric-num">{qualifying_count}</div><div class="metric-sub">meeting current cutoffs</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-wrap"><div class="metric-label">Near cutoff</div><div class="metric-num">{near_count}</div><div class="metric-sub">borderline names kept in view</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-wrap"><div class="metric-label">List now</div><div class="metric-num">{list_now}</div><div class="metric-sub">top current recommendations</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-wrap"><div class="metric-label">Themes in view</div><div class="metric-num">{unique_themes}</div><div class="metric-sub">more specific industry tags</div></div>', unsafe_allow_html=True)

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
        "Theme": st.column_config.TextColumn("Theme", width="medium", disabled=True, help="Derived from company description plus sector and industry metadata."),
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
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="main_table",
        column_order=[
            "Bucket", "Ticker", "Company", "Theme", "Mkt Cap ($B)",
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
        save_clicked = st.button("Save scores", use_container_width=True)
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
