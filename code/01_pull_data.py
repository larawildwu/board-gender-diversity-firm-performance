"""
01_pull_data.py
---------------
Pull firm-level annual data from WRDS Compustat Global.

Output: data/raw/compustat_global_raw.parquet

Notes
-----
- Uses python-dotenv to load WRDS credentials from .env (never hardcoded).
- Saves as Parquet (columnar, compressed) rather than CSV for faster downstream reads.
- All paths are relative — do not use absolute paths.
"""

import os
from pathlib import Path

import pandas as pd
import wrds
from dotenv import load_dotenv

# ── Credentials ───────────────────────────────────────────────────────────────
load_dotenv()  # reads WRDS_USERNAME from .env
WRDS_USER = os.getenv("WRDS_USERNAME")
if not WRDS_USER:
    raise EnvironmentError(
        "WRDS_USERNAME not set.\n" "Copy .env.example → .env and fill in your username."
    )

# ── Output path — relative, never absolute ────────────────────────────────────
OUT_PATH = Path("data/raw/compustat_global_raw.parquet")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── European country codes (ISO 3-letter) ─────────────────────────────────────
EUROPEAN_COUNTRIES = (
    "'AUT','BEL','CHE','CZE','DEU','DNK','ESP','FIN',"
    "'FRA','GBR','GRC','HUN','IRL','ITA','LUX','NLD',"
    "'NOR','POL','PRT','ROU','SWE','SVK','SVN'"
)

# ── WRDS query ────────────────────────────────────────────────────────────────
QUERY = f"""
    SELECT
    gvkey,          -- firm identifier
    conm,           -- company name
    fyear,          -- fiscal year
    loc,            -- country code
    sich,           -- industry code
    at,             -- total assets
    sale,           -- net sales
    ib,             -- income before extraordinary items
    nicon,          -- net income consolidated
    capx,           -- capital expenditures
    dltt,           -- long-term debt
    dlc,            -- debt in current liabilities
    che,            -- cash and short-term investments
    ppent,          -- property, plant and equipment
    emp             -- employees
FROM
    comp_global_daily.g_funda
    
    WHERE
        loc IN ({EUROPEAN_COUNTRIES})
        AND fyear BETWEEN 2015 AND 2024
        AND indfmt = 'INDL'
        AND datafmt = 'HIST_STD'
        AND popsrc = 'I'
        AND consol = 'C'
        AND at > 0
        AND sale > 0
"""

print("Connecting to WRDS...")
db = wrds.Connection(wrds_username=WRDS_USER)

print("Pulling Compustat Global (this may take a minute)...")
df = db.raw_sql(QUERY)
db.close()

print(f"  Raw observations: {len(df):,}")
print(f"  Unique firms:     {df['gvkey'].nunique():,}")
print(f"  Years covered:    {df['fyear'].min()}–{df['fyear'].max()}")
print(f"  Countries:        {df['loc'].nunique()}")

# ── Save as Parquet ───────────────────────────────────────────────────────────
# Parquet is columnar + compressed → much faster than CSV for repeated reads.
# Document download date in a sidecar text file for reproducibility.
df.to_parquet(OUT_PATH, index=False)
print(f"\nSaved to {OUT_PATH}")

# Document download metadata (source, date, license)
meta = OUT_PATH.with_suffix(".meta.txt")
from datetime import date

meta.write_text(
    f"Source: WRDS Compustat Global (comp_global_daily.g_funda)\n"
    f"Downloaded: {date.today().isoformat()}\n"
    f"License: WRDS subscriber agreement\n"
    f"Query: European SME candidates, fiscal years 2005–2020\n"
    f"Rows: {len(df):,} | Firms: {df['gvkey'].nunique():,}\n"
)
print(f"Download metadata saved to {meta}")