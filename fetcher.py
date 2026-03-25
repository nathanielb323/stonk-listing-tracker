"""
fetcher.py — S&P 500 screening via yfinance
Fetches price + volume data, computes dollar-volume metrics, filters & scores.
"""

import time
import warnings
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

MIN_VOL_M    = 500    # minimum daily dollar volume ($M) — anything below this is unlistable
LOOKBACK     = 38     # calendar days to fetch (gives ~30 trading days with buffer)
TOP_N        = 80     # max stocks returned
CHUNK_SIZE   = 100    # tickers per yfinance batch
CHUNK_DELAY  = 1.2    # seconds between chunks


def get_sp500_tickers():
    """Fetch S&P 500 constituent list from Wikipedia."""
    try:
        table = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            attrs={"id": "constituents"},
        )[0]
        tickers = table["Symbol"].str.replace(".", "-", regex=False).tolist()
        meta = table.set_index("Symbol")[["Security", "GICS Sector"]].copy()
        meta.index = meta.index.str.replace(".", "-", regex=False)
        return tickers, meta
    except Exception as e:
        # Hardcoded fallback: a broad set of liquid S&P 500 stocks
        fallback = [
            "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","BRK-B","JPM","V",
            "XOM","UNH","JNJ","PG","MA","HD","CVX","MRK","ABBV","LLY","COST","AVGO",
            "KO","PEP","BAC","WMT","MCD","TMO","CSCO","ACN","ABT","ORCL","WFC","TXN",
            "ADBE","DHR","LIN","NFLX","CRM","QCOM","AMD","INTC","AMGN","HON","UPS",
            "GS","SBUX","IBM","GE","CAT","BA","MMM","RTX","NOW","INTU","ISRG","BKNG",
            "REGN","GILD","VRTX","SYK","ZTS","MDLZ","PLD","AMT","CCI","EQIX","DLR",
            "PLTR","HOOD","COIN","SOFI","RKLB","IONQ","NVAX","MSTR","SMCI","DKNG",
            "UBER","LYFT","ABNB","DASH","SNAP","PINS","RBLX","U","MTCH","BMBL",
        ]
        meta = pd.DataFrame(
            {"Security": fallback, "GICS Sector": [""] * len(fallback)},
            index=fallback,
        )
        return fallback, meta


def fetch_ohlcv(tickers: list) -> dict:
    """Batch-download daily close + volume for all tickers."""
    all_data = {}
    total_chunks = (len(tickers) + CHUNK_SIZE - 1) // CHUNK_SIZE

    for i, start in enumerate(range(0, len(tickers), CHUNK_SIZE)):
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
    """
    Calculate dollar-volume metrics and auto-score each ticker.
    Returns DataFrame sorted by auto_score desc, filtered to >= MIN_VOL_M.
    """
    rows = []
    for ticker, df in all_data.items():
        try:
            df = df.copy()
            df["dv"] = df["Close"] * df["Volume"] / 1e6  # dollar vol in $M

            today_vol = df["dv"].iloc[-1]
            yest_vol  = df["dv"].iloc[-2]
            avg_30d   = df["dv"].iloc[-min(30, len(df)) :].mean()

            if today_vol < MIN_VOL_M:
                continue

            dd_pct = (today_vol - yest_vol) / yest_vol  if yest_vol > 0 else 0
            mm_pct = (today_vol - avg_30d)  / avg_30d   if avg_30d  > 0 else 0

            # Volume score (0–5)
            if   today_vol >= 5000: vol_s = 5
            elif today_vol >= 2000: vol_s = 4
            elif today_vol >= 1000: vol_s = 3
            elif today_vol >= 750:  vol_s = 2.5
            elif today_vol >= 500:  vol_s = 2
            else:                   vol_s = 1

            # Trend bonuses
            dd_b = 1.0 if dd_pct > 0.05 else (0.5 if dd_pct > 0 else -0.5)
            mm_b = 1.0 if mm_pct > 0.10 else (0.5 if mm_pct > 0 else -0.5)

            rows.append({
                "ticker":        ticker,
                "today_vol_m":   round(today_vol, 0),
                "yest_vol_m":    round(yest_vol, 0),
                "avg_30d_vol_m": round(avg_30d, 0),
                "dd_pct":        round(dd_pct * 100, 2),   # stored as % for display
                "mm_pct":        round(mm_pct * 100, 2),
                "auto_score":    round(vol_s + dd_b + mm_b, 2),
                "current_price": round(df["Close"].iloc[-1], 2),
            })
        except Exception:
            pass

    df_out = pd.DataFrame(rows)
    if df_out.empty:
        return df_out
    return df_out.sort_values("auto_score", ascending=False).head(TOP_N).reset_index(drop=True)


def fetch_market_caps(tickers: list) -> dict:
    """Fetch market caps for a (small) filtered list of tickers."""
    caps = {}
    for ticker in tickers:
        try:
            fi = yf.Ticker(ticker).fast_info
            caps[ticker] = getattr(fi, "market_cap", None)
        except Exception:
            caps[ticker] = None
        time.sleep(0.08)
    return caps


def run_screen():
    """
    Full pipeline: fetch tickers → OHLCV → metrics → market caps.
    Returns (df_metrics, meta_df, caps_dict).
    Called by Streamlit with @st.cache_data(ttl=3600).
    """
    tickers, meta = get_sp500_tickers()
    ohlcv         = fetch_ohlcv(tickers)
    df            = compute_metrics(ohlcv)
    caps          = fetch_market_caps(df["ticker"].tolist()) if not df.empty else {}
    return df, meta, caps
