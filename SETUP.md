# Cascade Listing Tracker — Setup Guide

## What you're deploying
A Streamlit web app that screens all S&P 500 stocks daily for equity perp listing candidates.
Team members can view the dashboard and edit manual scores (narrative, HL status, momentum, MM feasibility) directly in the browser.
All free, no credit card needed.

---

## Step 1 — Set up Supabase (shared database, ~5 min)

1. Go to [supabase.com](https://supabase.com) → **Start your project** → sign in with GitHub
2. Create a new project (any name, e.g. `cascade-tracker`), pick a region close to your team
3. Once the project is ready, go to **SQL Editor** and run this once:

```sql
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
```

4. Go to **Project Settings → API** and copy:
   - **Project URL** (looks like `https://abcdef.supabase.co`)
   - **anon public** key (the long one under "Project API keys")

---

## Step 2 — Push to GitHub (~3 min)

```bash
cd cascade-tracker
git init
git add .
git commit -m "Initial Cascade listing tracker"
gh repo create cascade-tracker --private --push --source=.
```

> The `.gitignore` already excludes `secrets.toml` so your keys stay private.

---

## Step 3 — Deploy to Streamlit Community Cloud (~5 min)

1. Go to [share.streamlit.io](https://share.streamlit.io) → sign in with GitHub
2. Click **New app** → select your `cascade-tracker` repo → main branch → `app.py`
3. Before deploying, click **Advanced settings → Secrets** and paste:

```toml
[supabase]
url = "https://YOUR_PROJECT_ID.supabase.co"
key = "YOUR_ANON_PUBLIC_KEY"
```

4. Hit **Deploy** — it'll be live at `https://your-app-name.streamlit.app` in ~2 min

Share that URL with Lucas, Patrick, and the rest of the team. Done.

---

## How the tracker works

| Feature | Detail |
|---|---|
| **Data source** | yfinance (Yahoo Finance) — free, no API key |
| **Screen universe** | All ~500 S&P 500 stocks |
| **Min filter** | ≥$500M daily dollar volume |
| **Refresh** | Click "🔄 Refresh Market Data" — data cached 1 hour to avoid rate limits |
| **Manual scores** | Click any cell in columns M–P or Notes to edit inline |
| **Save** | Hit "💾 Save Scores" — writes to Supabase, available to the whole team instantly |
| **Auto score** | Calculated from volume size + D/D trend + M/M trend |
| **Full R/R score** | Auto score + your weighted manual inputs |

---

## Scoring guide

| Column | What to score | Scale |
|---|---|---|
| **M: Narrative** | Community/tradfi buzz | 5 = RKLB-level cult, 1 = nobody's heard of it |
| **N: Not on HL** | Is it NOT yet on Hyperliquid or Ondo? | 1 = first-mover opp, 0 = already there |
| **O: Momentum** | Price trend | 5 = building strongly, not overextended; 1 = declining |
| **P: MM Feas.** | Can jpeg quote this market? | 5 = confirmed easy; confirm before scoring 4+ |

**R/R thresholds:** 🟢 ≥8 LIST NOW · 🟡 5.5–8 MONITOR · ⚪ 4–5.5 WATCH · ⚫ SKIP

---

## Running locally (for testing)

```bash
pip install -r requirements.txt
# Fill in .streamlit/secrets.toml with your Supabase creds
streamlit run app.py
```
