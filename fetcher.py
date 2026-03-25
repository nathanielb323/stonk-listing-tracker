"""
fetcher.py — S&P 500 screening via yfinance
Fetches price + volume data, computes dollar-volume metrics, and enriches
filtered candidates with market-cap + company-description metadata.
"""

import re
import time
import warnings
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

DEFAULT_MIN_VOL_M = 500
LOOKBACK = 38
TOP_N = 120
CHUNK_SIZE = 100
CHUNK_DELAY = 1.2
PROFILE_DELAY = 0.08


def get_sp500_tickers():
    """Fetch S&P 500 constituent list from Wikipedia."""
    try:
        table = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            attrs={"id": "constituents"},
        )[0]
        tickers = table["Symbol"].str.replace(".", "-", regex=False).tolist()
        meta = table.set_index("Symbol")[["Security", "GICS Sector", "GICS Sub-Industry"]].copy()
        meta.index = meta.index.str.replace(".", "-", regex=False)
        return tickers, meta
    except Exception:
        fallback = [
            "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "JPM", "V",
            "XOM", "UNH", "JNJ", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "LLY", "COST", "AVGO",
            "KO", "PEP", "BAC", "WMT", "MCD", "TMO", "CSCO", "ACN", "ABT", "ORCL", "WFC", "TXN",
            "ADBE", "DHR", "LIN", "NFLX", "CRM", "QCOM", "AMD", "INTC", "AMGN", "HON", "UPS",
            "GS", "SBUX", "IBM", "GE", "CAT", "BA", "MMM", "RTX", "NOW", "INTU", "ISRG", "BKNG",
            "REGN", "GILD", "VRTX", "SYK", "ZTS", "MDLZ", "PLD", "AMT", "CCI", "EQIX", "DLR",
            "PLTR", "HOOD", "COIN", "SOFI", "RKLB", "IONQ", "SMCI", "UBER", "ABNB", "DASH",
        ]
        meta = pd.DataFrame(
            {
                "Security": fallback,
                "GICS Sector": [""] * len(fallback),
                "GICS Sub-Industry": [""] * len(fallback),
            },
            index=fallback,
        )
        return fallback, meta


def fetch_ohlcv(tickers: list) -> dict:
    """Batch-download daily close + volume for all tickers."""
    all_data = {}
    for start in range(0, len(tickers), CHUNK_SIZE):
        chunk = tickers[start : start + CHUNK_SIZE]
        try:
            raw = yf.download(
                chunk,
                period=f"{LOOKBACK}d",
                interval="1d",
                auto_adjust=True,
                group_by="ticker",
                progress=False,
                threads=True,
            )
            for ticker in chunk:
                try:
                    df = (
                        raw[ticker][["Close", "Volume"]].dropna()
                        if len(chunk) > 1
                        else raw[["Close", "Volume"]].dropna()
                    )
                    if len(df) >= 5:
                        all_data[ticker] = df
                except Exception:
                    pass
        except Exception:
            pass

        if start + CHUNK_SIZE < len(tickers):
            time.sleep(CHUNK_DELAY)

    return all_data


def compute_metrics(all_data: dict) -> pd.DataFrame:
    """Calculate dollar-volume metrics and auto-score each ticker."""
    rows = []
    for ticker, df in all_data.items():
        try:
            local_df = df.copy()
            local_df["dv"] = local_df["Close"] * local_df["Volume"] / 1e6

            today_vol = float(local_df["dv"].iloc[-1])
            yest_vol = float(local_df["dv"].iloc[-2])
            avg_30d = float(local_df["dv"].iloc[-min(30, len(local_df)) :].mean())

            dd_pct = (today_vol - yest_vol) / yest_vol if yest_vol > 0 else 0
            mm_pct = (today_vol - avg_30d) / avg_30d if avg_30d > 0 else 0

            if today_vol >= 5000:
                vol_s = 5
            elif today_vol >= 2000:
                vol_s = 4
            elif today_vol >= 1000:
                vol_s = 3
            elif today_vol >= 750:
                vol_s = 2.5
            elif today_vol >= 500:
                vol_s = 2
            else:
                vol_s = 1

            dd_b = 1.0 if dd_pct > 0.05 else (0.5 if dd_pct > 0 else -0.5)
            mm_b = 1.0 if mm_pct > 0.10 else (0.5 if mm_pct > 0 else -0.5)

            rows.append(
                {
                    "ticker": ticker,
                    "today_vol_m": round(today_vol, 0),
                    "yest_vol_m": round(yest_vol, 0),
                    "avg_30d_vol_m": round(avg_30d, 0),
                    "dd_pct": round(dd_pct * 100, 2),
                    "mm_pct": round(mm_pct * 100, 2),
                    "auto_score": round(vol_s + dd_b + mm_b, 2),
                    "current_price": round(float(local_df["Close"].iloc[-1]), 2),
                }
            )
        except Exception:
            pass

    df_out = pd.DataFrame(rows)
    if df_out.empty:
        return df_out
    return df_out.sort_values(["today_vol_m", "auto_score"], ascending=False).head(TOP_N).reset_index(drop=True)


def _clean_summary(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def fetch_company_profiles(tickers: list) -> dict:
    """Fetch market cap + long business summary for a filtered list of tickers."""
    profiles = {}
    for ticker in tickers:
        profile = {"market_cap": None, "summary": ""}
        try:
            t = yf.Ticker(ticker)
            fi = getattr(t, "fast_info", None)
            if fi is not None:
                profile["market_cap"] = getattr(fi, "market_cap", None)

            info = getattr(t, "info", {}) or {}
            if profile["market_cap"] is None:
                profile["market_cap"] = info.get("marketCap")
            profile["summary"] = _clean_summary(info.get("longBusinessSummary") or info.get("description") or "")
        except Exception:
            pass

        profiles[ticker] = profile
        time.sleep(PROFILE_DELAY)
    return profiles


def run_screen():
    """
    Full pipeline: fetch tickers → OHLCV → metrics → company profiles.
    Returns (df_metrics, meta_df, profiles_dict).
    """
    tickers, meta = get_sp500_tickers()
    ohlcv = fetch_ohlcv(tickers)
    df = compute_metrics(ohlcv)
    profiles = fetch_company_profiles(df["ticker"].tolist()) if not df.empty else {}
    return df, meta, profiles
