# FIXED app.py

from datetime import datetime
import pandas as pd
import streamlit as st

import db
import fetcher

st.set_page_config(page_title="Cascade | Listing Tracker", layout="wide")

CURRENT_CASCADE_MARKETS = {
    "TSLA","CRCL","HOOD","AMD","PLTR","COIN","NVDA","GOOGL","META","TSM",
}

@st.cache_data(ttl=3600)
def load_market_data():
    return fetcher.run_screen()

@st.cache_data(ttl=3600)
def build_base_rows(df_market, meta, profiles):
    rows = []
    for _, row in df_market.iterrows():
        ticker = row["ticker"]
        profile = profiles.get(ticker) or {}  # FIX

        rows.append({
            "Ticker": ticker,
            "Price": row["current_price"],
            "Volume": row["today_vol_m"],
            "Auto Score": row["auto_score"],
            "Summary": profile.get("summary",""),
            "Market Cap": profile.get("market_cap"),
        })
    return pd.DataFrame(rows)

st.title("Markets")

if "data" not in st.session_state:
    st.session_state.data = None

if st.button("Refresh"):
    load_market_data.clear()
    st.session_state.data = None

if st.session_state.data is None:
    df_market, meta, profiles = load_market_data()
    st.session_state.data = (df_market, meta, profiles)
else:
    df_market, meta, profiles = st.session_state.data

df = build_base_rows(df_market, meta, profiles)
st.dataframe(df)
