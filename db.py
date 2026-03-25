"""
db.py — Supabase persistence layer for manual scores
=====================================================
Reads/writes the `stock_scores` table in your Supabase project.

Table schema (run once in Supabase SQL editor):

    CREATE TABLE stock_scores (
        ticker      TEXT PRIMARY KEY,
        narrative   INTEGER,
        not_hl      INTEGER,
        price_mom   INTEGER,
        mm_feas     INTEGER,
        notes       TEXT DEFAULT '',
        updated_at  TIMESTAMPTZ DEFAULT NOW(),
        updated_by  TEXT DEFAULT ''
    );

Credentials come from .streamlit/secrets.toml:
    [supabase]
    url = "https://xxxx.supabase.co"
    key = "your-anon-public-key"
"""

import streamlit as st

# ── Lazy client initialisation ────────────────────────────────────────────────
_client = None

def _get_client():
    global _client
    if _client is not None:
        return _client
    try:
        from supabase import create_client
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        _client = create_client(url, key)
        return _client
    except Exception as e:
        # Will surface as a warning; app still works (scores just won't persist)
        st.warning(
            f"⚠️ Supabase not configured — scores won't be saved between sessions. "
            f"See README.md to set up. ({e})"
        )
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def load_scores() -> dict:
    """
    Returns a dict: { "AAPL": {"narrative": 4, "not_hl": 1, ...}, ... }
    Falls back to empty dict if Supabase is unavailable.
    """
    client = _get_client()
    if client is None:
        return {}
    try:
        res = client.table("stock_scores").select("*").execute()
        scores = {}
        for row in res.data:
            ticker = row.pop("ticker")
            row.pop("updated_at", None)
            row.pop("updated_by", None)
            # Strip None values so the UI treats them as "not yet scored"
            scores[ticker] = {k: v for k, v in row.items() if v is not None}
        return scores
    except Exception as e:
        st.error(f"Failed to load scores from Supabase: {e}")
        return {}


def save_scores(scores: dict) -> bool:
    """
    Upserts scores for all tickers in the dict.
    scores format: { "AAPL": {"narrative": 4, "not_hl": 1, "price_mom": 3, "mm_feas": 5, "notes": "..."} }
    Returns True on success, False on failure.
    """
    client = _get_client()
    if client is None:
        return False
    try:
        from datetime import datetime, timezone
        rows = []
        for ticker, data in scores.items():
            row = {"ticker": ticker, "updated_at": datetime.now(timezone.utc).isoformat()}
            for field in ["narrative", "not_hl", "price_mom", "mm_feas", "notes"]:
                if field in data:
                    row[field] = data[field]
            rows.append(row)

        if rows:
            client.table("stock_scores").upsert(rows, on_conflict="ticker").execute()
        return True
    except Exception as e:
        st.error(f"Failed to save scores to Supabase: {e}")
        return False


def delete_score(ticker: str) -> bool:
    """Remove a ticker's manual scores entirely."""
    client = _get_client()
    if client is None:
        return False
    try:
        client.table("stock_scores").delete().eq("ticker", ticker).execute()
        return True
    except Exception as e:
        st.error(f"Failed to delete score for {ticker}: {e}")
        return False
