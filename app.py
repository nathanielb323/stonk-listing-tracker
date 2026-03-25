"""
Cascade Equity Perp Listing Tracker
===================================
Updated Streamlit dashboard with:
- current Cascade markets excluded
- derived theme column from company descriptions
- adjustable cutoff controls
- near-cutoff rows
- black and white UI
- adjustable ranking weights + recommendation thresholds
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
    ("AI / Model Infra", ["artificial intelligence", " ai ", "machine learning", "model", "gpu", "accelerator", "data center", "cloud platform"]),
    ("Quantum", ["quantum", "qubit"]),
    ("Crypto / Exchange", ["crypto", "cryptocurrency", "digital asset", "exchange", "wallet", "blockchain", "stablecoin"]),
    ("Broker / Fintech", ["broker", "brokerage", "trading platform", "payments", "consumer finance", "banking", "lending", "financial technology", "fintech"]),
    ("Space / Defense", ["space", "satellite", "defense", "missile", "aerospace", "launch"]),
    ("Semis / Compute", ["semiconductor", "chip", "fab", "processor", "memory", "analog", "microcontroller"]),
    ("Cybersecurity", ["security", "cyber", "identity", "threat", "endpoint", "firewall"]),
    ("EV / Autonomy", ["electric vehicle", " ev ", "autonomous", "autonomy", "robotaxi", "battery"]),
    ("Robotics / Industrial Automation", ["robot", "automation", "factory", "industrial software", "motion control"]),
    ("Cloud / Enterprise Software", ["software", "cloud", "saas", "workflow", "enterprise", "developer"]),
    ("Biotech / GLP-1 / Life Sciences", ["biotech", "therapeutic", "pharmaceutical", "drug", "obesity", "glp-1", "clinical"]),
    ("Consumer / Internet", ["social", "media", "advertising", "marketplace", "e-commerce", "consumer internet", "streaming"]),
    ("Energy / Power", ["energy", "oil", "gas", "utility", "power", "grid", "solar", "nuclear"]),
]

st.markdown(
    """
<style>
    .stApp {
        background: #ffffff;
        color: #111111;
    }
    .block-container {
        padding-top: 1.15rem;
        padding-bottom: 2rem;
    }
    section[data-testid="stSidebar"] {
        background: #fafafa;
        border-right: 1px solid #e6e6e6;
    }
    .hero {
        background: #ffffff;
        border: 1px solid #dedede;
        border-radius: 20px;
        padding: 24px 26px 20px 26px;
        margin-bottom: 18px;
    }
    .hero-title {
        font-size: 2.05rem;
        font-weight: 700;
        color: #111111;
        letter-spacing: -0.04em;
        margin: 0;
    }
    .hero-subtitle {
        color: #5f5f5f;
        font-size: 0.95rem;
        margin-top: 8px;
    }
    .metric-wrap {
        background: #ffffff;
        border: 1px solid #dedede;
        border-radius: 18px;
        padding: 18px 18px 14px 18px;
        min-height: 108px;
    }
    .metric-label {
        color: #6a6a6a;
        font-size: 0.82rem;
        margin-bottom: 8px;
    }
    .metric-num {
        color: #111111;
        font-size: 1.85rem;
        font-weight: 700;
        line-height: 1.05;
        letter-spacing: -0.04em;
    }
    .metric-sub {
        color: #6a6a6a;
        font-size: 0.84rem;
        margin-top: 6px;
    }
    .panel {
        background: #ffffff;
        border: 1px solid #dedede;
        border-radius: 20px;
        padding: 18px 18px 14px 18px;
        margin-top: 12px;
    }
    .panel h3 {
        margin-top: 0;
        margin-bottom: 6px;
        font-size: 1.08rem;
        letter-spacing: -0.03em;
        color: #111111;
    }
    .panel p {
        color: #666666;
        font-size: 0.9rem;
        margin-top: 0;
    }
    div[data-testid="stButton"] button {
        border-radius: 999px;
        border: 1px solid #111111;
        background: #111111;
        color: #ffffff;
        font-weight: 600;
        box-shadow: none;
    }
    div[data-testid="stButton"] button:hover {
        background: #222222;
        border-color: #222222;
        color: #ffffff;
    }
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        border-radius: 18px;
        overflow: hidden;
        border: 1px solid #dedede;
    }
    .footer-note {
        color: #777777;
        font-size: 0.77rem;
        text-align: center;
        margin-top: 10px;
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


def classify_theme(company: str, sector: str, sub_industry: str, summary: str) -> str:
    text = f" {company} {sector} {sub_industry} {summary} ".lower()
    for label, keywords in THEME_RULES:
        if any(keyword in text for keyword in keywords):
            return label

    sector_text = f"{sector} {sub_industry}".lower()
    if "financial" in sector_text:
        return "Financials"
    if "health" in sector_text:
        return "Healthcare"
    if "industrial" in sector_text:
        return "Industrials"
    if "energy" in sector_text:
        return "Energy"
    if "communication" in sector_text:
        return "Media / Communications"
    if "consumer" in sector_text:
        return "Consumer"
    if "information technology" in sector_text:
        return "General Tech"
    return "General"


@st.cache_data(ttl=3600, show_spinner=False)
def build_base_rows(df_market, meta, profiles):
    rows = []
    for _, row in df_market.iterrows():
        ticker = row["ticker"]
        company = meta.loc[ticker, "Security"] if ticker in meta.index else ticker
        sector = meta.loc[ticker, "GICS Sector"] if ticker in meta.index else ""
        sub_industry = meta.loc[ticker, "GICS Sub-Industry"] if ticker in meta.index and "GICS Sub-Industry" in meta.columns else ""
        profile = profiles.get(ticker) or {}
        summary = profile.get("summary", "")
        market_cap = profile.get("market_cap")

        rows.append(
            {
                "Ticker": ticker,
                "Company": company,
                "Sector": sector,
                "Sub-Industry": sub_industry,
                "Theme": classify_theme(company, sector, sub_industry, summary),
                "Business Summary": summary,
                "Price ($)": row["current_price"],
                "Mkt Cap ($B)": round(market_cap / 1e9, 1) if market_cap else None,
                "Today Vol ($M)": int(row["today_vol_m"]),
                "30D Avg Vol ($M)": int(row["avg_30d_vol_m"]),
                "D/D %": row["dd_pct"],
                "M/M %": row["mm_pct"],
                "Auto Score": row["auto_score"],
            }
        )
    return pd.DataFrame(rows)


def recommendation_from_score(score: float, list_now_min: float, monitor_min: float, watch_min: float) -> str:
    if score >= list_now_min:
        return "🟢 LIST NOW"
    if score >= monitor_min:
        return "🟡 MONITOR CLOSELY"
    if score >= watch_min:
        return "⚪ WATCH"
    return "⚫ SKIP"


def build_display_df(
    base_df,
    scores_db,
    min_vol,
    min_score,
    near_cutoff_count,
    exclude_current,
    selected_themes,
    vol_buffer,
    score_buffer,
    narrative_weight,
    not_hl_weight,
    momentum_weight,
    mm_weight,
    list_now_min,
    monitor_min,
    watch_min,
):
    if base_df.empty:
        return base_df

    working = base_df.copy()
    if exclude_current:
        working = working[~working["Ticker"].isin(CURRENT_CASCADE_MARKETS)]

    if selected_themes and "All" not in selected_themes:
        working = working[working["Theme"].isin(selected_themes)]

    qualified = working[
        (working["Today Vol ($M)"] >= min_vol) &
        (working["Auto Score"] >= min_score)
    ].copy()
    qualified["Bucket"] = "Qualified"

    near_cutoff = working[
        (
            ((working["Today Vol ($M)"] < min_vol) & (working["Today Vol ($M)"] >= max(0, min_vol - vol_buffer))) |
            ((working["Auto Score"] < min_score) & (working["Auto Score"] >= max(0, min_score - score_buffer)))
        )
    ].copy()
    near_cutoff = near_cutoff[~near_cutoff["Ticker"].isin(qualified["Ticker"])]
    near_cutoff = near_cutoff.sort_values(["Today Vol ($M)", "Auto Score"], ascending=False).head(near_cutoff_count)
    near_cutoff["Bucket"] = "Near Cutoff"

    df = pd.concat([qualified, near_cutoff], ignore_index=True)
    if df.empty:
        return df

    m_vals, n_vals, o_vals, p_vals, notes_vals = [], [], [], [], []
    full_scores, recs, reasons = [], [], []

    for _, row in df.iterrows():
        ticker = row["Ticker"]
        ms = scores_db.get(ticker, {})
        narrative = ms.get("narrative")
        not_hl = ms.get("not_hl")
        price_mom = ms.get("price_mom")
        mm_feas = ms.get("mm_feas")
        notes = ms.get("notes", "")

        bonus = 0.0
        reason_parts = [f"Auto {row['Auto Score']:.1f}"]
        if narrative is not None:
            add = (narrative / 5) * narrative_weight
            bonus += add
            reason_parts.append(f"Narrative +{add:.1f}")
        if not_hl is not None:
            add = not_hl * not_hl_weight
            bonus += add
            reason_parts.append(f"Not on HL +{add:.1f}")
        if price_mom is not None:
            add = (price_mom / 5) * momentum_weight
            bonus += add
            reason_parts.append(f"Momentum +{add:.1f}")
        if mm_feas is not None:
            add = (mm_feas / 5) * mm_weight
            bonus += add
            reason_parts.append(f"MM +{add:.1f}")

        score = round(float(row["Auto Score"]) + bonus, 1)
        rec = recommendation_from_score(score, list_now_min, monitor_min, watch_min)

        m_vals.append(narrative)
        n_vals.append(not_hl)
        o_vals.append(price_mom)
        p_vals.append(mm_feas)
        notes_vals.append(notes)
        full_scores.append(score)
        recs.append(rec)
        reasons.append(" | ".join(reason_parts))

    df["M: Narrative"] = m_vals
    df["N: Not on HL"] = n_vals
    df["O: Momentum"] = o_vals
    df["P: MM Feas."] = p_vals
    df["Full R/R"] = full_scores
    df["Recommendation"] = recs
    df["Score Detail"] = reasons
    df["Notes"] = notes_vals

    order_cols = [
        "Bucket", "Ticker", "Company", "Theme", "Sector", "Sub-Industry",
        "Price ($)", "Mkt Cap ($B)", "Today Vol ($M)", "30D Avg Vol ($M)", "D/D %", "M/M %",
        "Auto Score", "M: Narrative", "N: Not on HL", "O: Momentum", "P: MM Feas.",
        "Full R/R", "Recommendation", "Score Detail", "Notes", "Business Summary",
    ]
    df = df[order_cols]
    return df.sort_values(["Bucket", "Full R/R", "Today Vol ($M)"], ascending=[True, False, False]).reset_index(drop=True)


with st.sidebar:
    st.markdown("### Controls")
    if st.button("Refresh Market Data", use_container_width=True):
        load_market_data.clear()
        build_base_rows.clear()
        st.session_state.data = None
        st.session_state.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.rerun()

    st.divider()
    st.markdown("### Screen")
    min_vol = st.slider("Min daily dollar volume ($M)", 100, 5000, 500, step=50)
    min_score = st.slider("Min auto score", 0.0, 7.0, 0.0, step=0.5)
    near_cutoff_count = st.slider("Near-cutoff extras", 0, 30, 10, step=1)
    vol_buffer = st.slider("Near-cutoff volume window ($M)", 25, 500, 150, step=25)
    score_buffer = st.slider("Near-cutoff auto-score window", 0.5, 3.0, 1.0, step=0.5)
    exclude_current = st.toggle("Exclude currently live Cascade markets", value=True)

    st.divider()
    st.markdown("### Ranking Weights")
    narrative_weight = st.slider("Narrative weight", 0.0, 4.0, 2.0, step=0.5)
    not_hl_weight = st.slider("Not on HL weight", 0.0, 3.0, 1.5, step=0.5)
    momentum_weight = st.slider("Momentum weight", 0.0, 3.0, 1.0, step=0.5)
    mm_weight = st.slider("MM feasibility weight", 0.0, 3.0, 1.0, step=0.5)

    st.divider()
    st.markdown("### Recommendation Bands")
    list_now_min = st.slider("List Now minimum", 4.0, 12.0, 8.0, step=0.5)
    monitor_min = st.slider("Monitor minimum", 2.0, 10.0, 5.5, step=0.5)
    watch_min = st.slider("Watch minimum", 0.0, 8.0, 4.0, step=0.5)

    if monitor_min > list_now_min:
        monitor_min = list_now_min
    if watch_min > monitor_min:
        watch_min = monitor_min

    st.divider()
    st.markdown("### Recommendation Filter")
    show_rec = st.multiselect(
        "Show recommendations",
        ["🟢 LIST NOW", "🟡 MONITOR CLOSELY", "⚪ WATCH", "⚫ SKIP"],
        default=["🟢 LIST NOW", "🟡 MONITOR CLOSELY", "⚪ WATCH", "⚫ SKIP"],
    )

refresh_ts = st.session_state.last_refresh or "Not yet loaded"
st.markdown(
    f"""
<div class="hero">
  <div class="hero-title">Markets</div>
  <div class="hero-subtitle">S&P 500 screen for equity perp listing candidates. Current Cascade markets excluded by default. Last refresh: {refresh_ts}</div>
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
all_themes = sorted(base_df["Theme"].dropna().unique().tolist()) if not base_df.empty else []
selected_themes = st.multiselect("Filter by theme", ["All"] + all_themes, default=["All"])

if selected_themes != ["All"] and "All" in selected_themes:
    selected_themes = [x for x in selected_themes if x != "All"]

df_display = build_display_df(
    base_df=base_df,
    scores_db=scores_db,
    min_vol=min_vol,
    min_score=min_score,
    near_cutoff_count=near_cutoff_count,
    exclude_current=exclude_current,
    selected_themes=selected_themes or ["All"],
    vol_buffer=vol_buffer,
    score_buffer=score_buffer,
    narrative_weight=narrative_weight,
    not_hl_weight=not_hl_weight,
    momentum_weight=momentum_weight,
    mm_weight=mm_weight,
    list_now_min=list_now_min,
    monitor_min=monitor_min,
    watch_min=watch_min,
)

if show_rec and not df_display.empty:
    df_display = df_display[df_display["Recommendation"].isin(show_rec)]

qualifying_count = int((df_display["Bucket"] == "Qualified").sum()) if not df_display.empty else 0
near_count = int((df_display["Bucket"] == "Near Cutoff").sum()) if not df_display.empty else 0
list_now = int((df_display["Recommendation"] == "🟢 LIST NOW").sum()) if not df_display.empty else 0
unique_themes = int(df_display["Theme"].nunique()) if not df_display.empty else 0

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="metric-wrap"><div class="metric-label">Qualified names</div><div class="metric-num">{qualifying_count}</div><div class="metric-sub">meeting current cutoffs</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-wrap"><div class="metric-label">Near cutoff</div><div class="metric-num">{near_count}</div><div class="metric-sub">extra rows for borderline names</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-wrap"><div class="metric-label">List now</div><div class="metric-num">{list_now}</div><div class="metric-sub">top current recommendations</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-wrap"><div class="metric-label">Themes in view</div><div class="metric-num">{unique_themes}</div><div class="metric-sub">derived from company descriptions</div></div>', unsafe_allow_html=True)

st.markdown(
    """
<div class="panel">
  <h3>How ranking works</h3>
  <p>Full R/R = Auto Score + manual bonuses. Auto Score comes from current dollar volume plus day-over-day and month-over-month trend strength. Manual bonuses use the adjustable weights in the sidebar for Narrative, Not on HL, Momentum, and MM Feasibility.</p>
</div>
""",
    unsafe_allow_html=True,
)

with st.expander("Current ranking formula and thresholds", expanded=False):
    st.markdown(
        f"""
- **Auto Score**: generated from liquidity and trend data
- **Narrative bonus**: `(Narrative / 5) × {narrative_weight:.1f}`
- **Not on HL bonus**: `Not on HL × {not_hl_weight:.1f}`
- **Momentum bonus**: `(Momentum / 5) × {momentum_weight:.1f}`
- **MM Feasibility bonus**: `(MM Feasibility / 5) × {mm_weight:.1f}`

**Recommendation bands**
- `🟢 LIST NOW` at **{list_now_min:.1f}+**
- `🟡 MONITOR CLOSELY` at **{monitor_min:.1f}+**
- `⚪ WATCH` at **{watch_min:.1f}+**
- `⚫ SKIP` below **{watch_min:.1f}**
"""
    )

if df_display.empty:
    st.info("No stocks match your current settings. Lower the volume or score thresholds, or add more near-cutoff rows.")
else:
    col_config = {
        "Bucket": st.column_config.TextColumn("Bucket", width="small", disabled=True),
        "Ticker": st.column_config.TextColumn("Ticker", width="small", disabled=True),
        "Company": st.column_config.TextColumn("Company", width="medium", disabled=True),
        "Theme": st.column_config.TextColumn("Theme", width="medium", disabled=True, help="Derived automatically from company description + sector metadata."),
        "Sector": st.column_config.TextColumn("Sector", width="medium", disabled=True),
        "Sub-Industry": st.column_config.TextColumn("Sub-Industry", width="medium", disabled=True),
        "Price ($)": st.column_config.NumberColumn("Price ($)", format="$%.2f", disabled=True),
        "Mkt Cap ($B)": st.column_config.NumberColumn("Mkt Cap ($B)", format="%.1f B", disabled=True),
        "Today Vol ($M)": st.column_config.NumberColumn("Today Vol ($M)", format="%,d", disabled=True),
        "30D Avg Vol ($M)": st.column_config.NumberColumn("30D Avg Vol ($M)", format="%,d", disabled=True),
        "D/D %": st.column_config.NumberColumn("D/D %", format="%.1f%%", disabled=True),
        "M/M %": st.column_config.NumberColumn("M/M %", format="%.1f%%", disabled=True),
        "Auto Score": st.column_config.NumberColumn("Auto Score", format="%.1f", disabled=True),
        "M: Narrative": st.column_config.NumberColumn("M: Narrative", min_value=1, max_value=5, step=1),
        "N: Not on HL": st.column_config.NumberColumn("N: Not on HL", min_value=0, max_value=1, step=1),
        "O: Momentum": st.column_config.NumberColumn("O: Momentum", min_value=1, max_value=5, step=1),
        "P: MM Feas.": st.column_config.NumberColumn("P: MM Feas.", min_value=1, max_value=5, step=1),
        "Full R/R": st.column_config.NumberColumn("Full R/R", format="%.1f", disabled=True),
        "Recommendation": st.column_config.TextColumn("Recommendation", width="medium", disabled=True),
        "Score Detail": st.column_config.TextColumn("Score Detail", width="large", disabled=True),
        "Notes": st.column_config.TextColumn("Notes", width="large"),
        "Business Summary": st.column_config.TextColumn("Business Summary", width="large", disabled=True),
    }

    edited_df = st.data_editor(
        df_display,
        column_config=col_config,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="main_table",
        column_order=[
            "Bucket", "Ticker", "Company", "Theme", "Sector", "Price ($)", "Mkt Cap ($B)",
            "Today Vol ($M)", "30D Avg Vol ($M)", "D/D %", "M/M %", "Auto Score",
            "M: Narrative", "N: Not on HL", "O: Momentum", "P: MM Feas.",
            "Full R/R", "Recommendation", "Score Detail", "Notes", "Business Summary",
        ],
    )

    # Recalculate live after edits so the table reflects current controls immediately
    if not edited_df.empty:
        detail_vals, full_vals, rec_vals = [], [], []
        for _, row in edited_df.iterrows():
            bonus = 0.0
            parts = [f"Auto {float(row['Auto Score']):.1f}"]
            if pd.notna(row.get("M: Narrative")):
                add = (float(row["M: Narrative"]) / 5) * narrative_weight
                bonus += add
                parts.append(f"Narrative +{add:.1f}")
            if pd.notna(row.get("N: Not on HL")):
                add = float(row["N: Not on HL"]) * not_hl_weight
                bonus += add
                parts.append(f"Not on HL +{add:.1f}")
            if pd.notna(row.get("O: Momentum")):
                add = (float(row["O: Momentum"]) / 5) * momentum_weight
                bonus += add
                parts.append(f"Momentum +{add:.1f}")
            if pd.notna(row.get("P: MM Feas.")):
                add = (float(row["P: MM Feas."]) / 5) * mm_weight
                bonus += add
                parts.append(f"MM +{add:.1f}")

            score = round(float(row["Auto Score"]) + bonus, 1)
            rec = recommendation_from_score(score, list_now_min, monitor_min, watch_min)
            full_vals.append(score)
            rec_vals.append(rec)
            detail_vals.append(" | ".join(parts))

        edited_df["Full R/R"] = full_vals
        edited_df["Recommendation"] = rec_vals
        edited_df["Score Detail"] = detail_vals

    save_col, status_col = st.columns([1, 4])
    with save_col:
        save_clicked = st.button("Save Scores", use_container_width=True)
    with status_col:
        if st.session_state.save_status:
            st.success(st.session_state.save_status)

    if save_clicked:
        new_scores = {}
        for _, row in edited_df.iterrows():
            ticker = row["Ticker"]
            entry = {}
            if pd.notna(row.get("M: Narrative")):
                entry["narrative"] = int(row["M: Narrative"])
            if pd.notna(row.get("N: Not on HL")):
                entry["not_hl"] = int(row["N: Not on HL"])
            if pd.notna(row.get("O: Momentum")):
                entry["price_mom"] = int(row["O: Momentum"])
            if pd.notna(row.get("P: MM Feas.")):
                entry["mm_feas"] = int(row["P: MM Feas."])
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
