"""
Cascade Equity Perp Listing Tracker
=====================================
Streamlit dashboard for tracking S&P 500 stocks as equity perp listing candidates.

Deploy: https://share.streamlit.io  (free)
Database: Supabase free tier (https://supabase.com)

Setup: see README.md
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime

import fetcher
import db

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cascade | Listing Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0f1117; }

    /* Hide default header padding */
    .block-container { padding-top: 1.5rem; }

    /* Title bar */
    .tracker-title {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 18px 28px;
        margin-bottom: 20px;
        border-left: 4px solid #4f8ef7;
    }
    .tracker-title h1 {
        color: #ffffff;
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: 0.5px;
    }
    .tracker-title p {
        color: #8899aa;
        font-size: 0.85rem;
        margin: 4px 0 0 0;
    }

    /* Metric cards */
    .metric-card {
        background: #1a1a2e;
        border-radius: 10px;
        padding: 14px 18px;
        border: 1px solid #2a2a4a;
        text-align: center;
    }
    .metric-num  { font-size: 1.8rem; font-weight: 700; color: #4f8ef7; }
    .metric-label { font-size: 0.75rem; color: #8899aa; text-transform: uppercase; letter-spacing: 1px; }

    /* Recommendation badges */
    .badge-green  { color: #00c853; font-weight: 700; }
    .badge-yellow { color: #ffc107; font-weight: 700; }
    .badge-red    { color: #ff5252; font-weight: 700; }
    .badge-grey   { color: #888888; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #111827; }
    section[data-testid="stSidebar"] .stMarkdown h3 { color: #4f8ef7; }

    /* Table tweaks */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* Save button */
    div[data-testid="stButton"] button {
        background-color: #4f8ef7;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    div[data-testid="stButton"] button:hover { background-color: #3a7bd5; }
</style>
""", unsafe_allow_html=True)


# ── Session state defaults ────────────────────────────────────────────────────
if "data" not in st.session_state:
    st.session_state.data = None
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None
if "save_status" not in st.session_state:
    st.session_state.save_status = ""


# ── Cached data fetch (1 hour TTL to respect rate limits) ────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_market_data():
    return fetcher.run_screen()


def get_data():
    with st.spinner("📡 Screening S&P 500 via yfinance... (~2 min)"):
        df, meta, caps = load_market_data()
    return df, meta, caps


# ── Header ────────────────────────────────────────────────────────────────────
refresh_ts = st.session_state.last_refresh or "Not yet loaded"
st.markdown(f"""
<div class="tracker-title">
  <h1>📈 Cascade — Equity Perp Listing Tracker</h1>
  <p>S&P 500 screen · ≥$500M daily volume · Increasing momentum · Last refresh: {refresh_ts}</p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Controls")

    if st.button("🔄  Refresh Market Data", use_container_width=True):
        load_market_data.clear()
        st.session_state.data = None
        st.session_state.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.rerun()

    st.divider()
    st.markdown("### 🔍 Filters")

    min_vol = st.slider("Min daily volume ($M)", 500, 5000, 500, step=250)
    min_score = st.slider("Min auto score", 0.0, 7.0, 0.0, step=0.5)

    sectors_all = ["All sectors"]
    show_rec = st.multiselect(
        "Show recommendations",
        ["🟢 LIST NOW", "🟡 MONITOR CLOSELY", "⚪ WATCH", "⚫ SKIP", "🔴 VOL TOO LOW"],
        default=["🟢 LIST NOW", "🟡 MONITOR CLOSELY", "⚪ WATCH"],
    )

    st.divider()
    st.markdown("### 📖 Score Guide")
    st.markdown("""
**M – Narrative** (1–5)
5 = massive tradfi cult
3 = growing interest
1 = obscure

**N – Not on HL** (1 or 0)
1 = first-mover opportunity
0 = already on Hyperliquid

**O – Price Momentum** (1–5)
5 = strong trend, not overextended
3 = sideways
1 = declining

**P – MM Feasibility** (1–5)
5 = jpeg confirmed + easy
1 = MM declined

---
**R/R ≥ 8** → 🟢 List Now
**R/R 5.5–8** → 🟡 Monitor
**R/R 4–5.5** → ⚪ Watch
""")


# ── Load data ─────────────────────────────────────────────────────────────────
if st.session_state.data is None:
    df_market, meta, caps = get_data()
    st.session_state.data = (df_market, meta, caps)
    if st.session_state.last_refresh is None:
        st.session_state.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M")
else:
    df_market, meta, caps = st.session_state.data

# Load manual scores from Supabase
scores_db = db.load_scores()


# ── Merge market data with manual scores ──────────────────────────────────────
def build_display_df(df_market, meta, caps, scores_db, min_vol, min_score):
    rows = []
    for _, row in df_market.iterrows():
        ticker = row["ticker"]
        if row["today_vol_m"] < min_vol:
            continue
        if row["auto_score"] < min_score:
            continue

        ms = scores_db.get(ticker, {})
        cap_b = caps.get(ticker)
        company = meta.loc[ticker, "Security"] if ticker in meta.index else ticker
        sector  = meta.loc[ticker, "GICS Sector"] if ticker in meta.index else ""

        narrative = ms.get("narrative", None)
        not_hl    = ms.get("not_hl", None)
        price_mom = ms.get("price_mom", None)
        mm_feas   = ms.get("mm_feas", None)
        notes     = ms.get("notes", "")

        # Full R/R score
        auto = row["auto_score"]
        manual_bonus = 0
        scored_count = 0
        if narrative is not None:
            manual_bonus += (narrative / 5) * 2; scored_count += 1
        if not_hl is not None:
            manual_bonus += not_hl * 1.5; scored_count += 1
        if price_mom is not None:
            manual_bonus += (price_mom / 5) * 1; scored_count += 1
        if mm_feas is not None:
            manual_bonus += (mm_feas / 5) * 1; scored_count += 1
        full_score = round(auto + manual_bonus, 1)

        if full_score >= 8:
            rec = "🟢 LIST NOW"
        elif full_score >= 5.5:
            rec = "🟡 MONITOR CLOSELY"
        elif full_score >= 4:
            rec = "⚪ WATCH"
        else:
            rec = "⚫ SKIP"

        rows.append({
            "Ticker":       ticker,
            "Company":      company,
            "Sector":       sector,
            "Price ($)":    row["current_price"],
            "Mkt Cap ($B)": round(cap_b / 1e9, 1) if cap_b else None,
            "Today Vol ($M)": int(row["today_vol_m"]),
            "D/D %":        row["dd_pct"],
            "M/M %":        row["mm_pct"],
            "Auto Score":   auto,
            "M: Narrative": narrative,
            "N: Not on HL": not_hl,
            "O: Momentum":  price_mom,
            "P: MM Feas.":  mm_feas,
            "Full R/R":     full_score,
            "Recommendation": rec,
            "Notes":        notes,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("Full R/R", ascending=False).reset_index(drop=True)


df_display = build_display_df(df_market, meta, caps, scores_db, min_vol, min_score)

# Apply recommendation filter
if show_rec and not df_display.empty:
    df_display = df_display[df_display["Recommendation"].isin(show_rec)]


# ── Metric cards ──────────────────────────────────────────────────────────────
total = len(df_display)
list_now = (df_display["Recommendation"] == "🟢 LIST NOW").sum() if total > 0 else 0
monitor  = (df_display["Recommendation"] == "🟡 MONITOR CLOSELY").sum() if total > 0 else 0
scored   = df_display[["M: Narrative","N: Not on HL","O: Momentum","P: MM Feas."]].notna().any(axis=1).sum() if total > 0 else 0

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-card"><div class="metric-num">{total}</div><div class="metric-label">Qualifying Stocks</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="metric-num badge-green">{list_now}</div><div class="metric-label">List Now</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card"><div class="metric-num badge-yellow">{monitor}</div><div class="metric-label">Monitor Closely</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><div class="metric-num">{scored}</div><div class="metric-label">Manually Scored</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ── Editable table ────────────────────────────────────────────────────────────
st.markdown("#### 📊 Stock Watchlist — click any cell in columns M–P or Notes to edit")

if df_display.empty:
    st.info("No stocks match your current filters. Try lowering the min volume or score threshold.")
else:
    # Column config: lock auto-cols, allow editing of manual score cols
    col_config = {
        "Ticker":        st.column_config.TextColumn("Ticker", width="small", disabled=True),
        "Company":       st.column_config.TextColumn("Company", width="medium", disabled=True),
        "Sector":        st.column_config.TextColumn("Sector", width="medium", disabled=True),
        "Price ($)":     st.column_config.NumberColumn("Price ($)", format="$%.2f", disabled=True),
        "Mkt Cap ($B)":  st.column_config.NumberColumn("Mkt Cap ($B)", format="%.1f B", disabled=True),
        "Today Vol ($M)":st.column_config.NumberColumn("Today Vol ($M)", format="%,d", disabled=True),
        "D/D %":         st.column_config.NumberColumn("D/D %", format="%.1f%%", disabled=True),
        "M/M %":         st.column_config.NumberColumn("M/M %", format="%.1f%%", disabled=True),
        "Auto Score":    st.column_config.NumberColumn("Auto Score", format="%.1f", disabled=True, help="Volume + trend score (auto-calculated)"),
        "M: Narrative":  st.column_config.NumberColumn("M: Narrative", min_value=1, max_value=5, step=1,
                            help="1–5: Community/tradfi buzz. 5=massive cult (RKLB-level)"),
        "N: Not on HL":  st.column_config.NumberColumn("N: Not on HL", min_value=0, max_value=1, step=1,
                            help="1=not yet on Hyperliquid/Ondo (first-mover), 0=already listed"),
        "O: Momentum":   st.column_config.NumberColumn("O: Momentum", min_value=1, max_value=5, step=1,
                            help="1–5: Price building (5) vs declining (1). Avoid terminal velocity."),
        "P: MM Feas.":   st.column_config.NumberColumn("P: MM Feas.", min_value=1, max_value=5, step=1,
                            help="1–5: Can jpeg quote this market? Confirm before scoring 4+"),
        "Full R/R":      st.column_config.NumberColumn("Full R/R", format="%.1f", disabled=True),
        "Recommendation":st.column_config.TextColumn("Recommendation", width="medium", disabled=True),
        "Notes":         st.column_config.TextColumn("Notes", width="large"),
    }

    edited_df = st.data_editor(
        df_display,
        column_config=col_config,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="main_table",
    )

    # Recalculate Full R/R live after edits
    def recalc_score(row):
        auto = row["Auto Score"]
        bonus = 0
        if pd.notna(row["M: Narrative"]):  bonus += (row["M: Narrative"] / 5) * 2
        if pd.notna(row["N: Not on HL"]):  bonus += row["N: Not on HL"] * 1.5
        if pd.notna(row["O: Momentum"]):   bonus += (row["O: Momentum"] / 5) * 1
        if pd.notna(row["P: MM Feas."]):   bonus += (row["P: MM Feas."] / 5) * 1
        score = round(auto + bonus, 1)
        if score >= 8:     return "🟢 LIST NOW"
        elif score >= 5.5: return "🟡 MONITOR CLOSELY"
        elif score >= 4:   return "⚪ WATCH"
        else:              return "⚫ SKIP"

    # ── Save button ───────────────────────────────────────────────────────────
    col_save, col_status = st.columns([1, 4])
    with col_save:
        save_clicked = st.button("💾  Save Scores", use_container_width=True)

    with col_status:
        if st.session_state.save_status:
            st.success(st.session_state.save_status)

    if save_clicked:
        new_scores = {}
        for _, row in edited_df.iterrows():
            ticker = row["Ticker"]
            entry = {}
            if pd.notna(row.get("M: Narrative")):  entry["narrative"]  = int(row["M: Narrative"])
            if pd.notna(row.get("N: Not on HL")):  entry["not_hl"]     = int(row["N: Not on HL"])
            if pd.notna(row.get("O: Momentum")):   entry["price_mom"]  = int(row["O: Momentum"])
            if pd.notna(row.get("P: MM Feas.")):   entry["mm_feas"]    = int(row["P: MM Feas."])
            if row.get("Notes"):                   entry["notes"]      = str(row["Notes"])
            if entry:
                new_scores[ticker] = entry

        with st.spinner("Saving to database..."):
            ok = db.save_scores(new_scores)

        if ok:
            st.session_state.save_status = f"✅ Saved scores for {len(new_scores)} stocks — {datetime.now().strftime('%H:%M:%S')}"
        else:
            st.session_state.save_status = "❌ Save failed — check your Supabase credentials in .streamlit/secrets.toml"
        st.rerun()


# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<p style='color:#444;font-size:0.75rem;text-align:center'>"
    "Data via yfinance (Yahoo Finance) · Scores stored in Supabase · "
    "Refresh once daily to avoid rate limits · Cascade internal tool</p>",
    unsafe_allow_html=True,
)
