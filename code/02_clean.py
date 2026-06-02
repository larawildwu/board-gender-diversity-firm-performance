"""
02_clean.py
-----------
Clean raw Compustat data, apply SME filter, construct variables.

Input:  data/raw/compustat_global_raw.parquet
Output: data/processed/panel_clean.parquet

Variable construction
---------------------
ROA                = nicon / at
Capital intensity  = capx / at
Firm size          = log(at)
Leverage           = (dltt + dlc) / at
Cash holdings      = che / at
Tangibility        = ppent / at
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
RAW_PATH = Path("data/raw/compustat_global_raw.parquet")
OUT_PATH = Path("data/processed/panel_clean.parquet")
LOG_PATH = Path("data/processed/clean_log.txt")

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading raw data...")
df = pd.read_parquet(RAW_PATH)
n_raw = len(df)

print(f"  Raw observations: {n_raw:,}")
print(f"  Raw firms: {df['gvkey'].nunique():,}")

# ── Basic cleaning ────────────────────────────────────────────────────────────
df = df.drop_duplicates()
df = df.dropna(subset=["gvkey", "fyear", "at"]).copy()

# Total assets must be positive for ratios
df = df[df["at"] > 0].copy()

# ── SME Filter ────────────────────────────────────────────────────────────────
# EU definition approximation:
# emp < 0.25 means fewer than 250 employees, because emp is in thousands.
# at <= 43 means total assets up to 43 million.
sme_mask = (df["emp"] < 0.25) | (df["at"] <= 43)
df = df[sme_mask].copy()

print(f"  After SME filter: {len(df):,} observations")

# ── Construct variables ───────────────────────────────────────────────────────
df["roa"] = df["nicon"] / df["at"]
df["capital_intensity"] = df["capx"] / df["at"]
df["firm_size"] = np.log(df["at"])
df["leverage"] = (df["dltt"].fillna(0) + df["dlc"].fillna(0)) / df["at"]
df["cash_holdings"] = df["che"] / df["at"]
df["tangibility"] = df["ppent"] / df["at"]

# ── Winsorize at 1%–99% ───────────────────────────────────────────────────────
def winsorize(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    lo = series.quantile(lower)
    hi = series.quantile(upper)
    return series.clip(lo, hi)

for col in [
    "roa",
    "capital_intensity",
    "firm_size",
    "leverage",
    "cash_holdings",
    "tangibility",
]:
    df[col] = winsorize(df[col])

# ── Drop observations with missing core variables ─────────────────────────────
core_vars = [
    "roa",
    "capital_intensity",
    "firm_size",
    "leverage",
    "cash_holdings",
    "tangibility",
]

n_before = len(df)
df = df.dropna(subset=core_vars).copy()

print(f"  After dropping missing core vars: {len(df):,} observations")
print(f"  Removed because of missing core vars: {n_before - len(df):,}")

# ── Require at least 3 observations per firm ──────────────────────────────────
obs_per_firm = df.groupby("gvkey")["fyear"].count()
valid_firms = obs_per_firm[obs_per_firm >= 3].index

n_before = len(df)
df = df[df["gvkey"].isin(valid_firms)].copy()

print(f"  After min-obs filter: {len(df):,} observations")
print(f"  Final firms: {df['gvkey'].nunique():,}")
print(f"  Countries: {df['loc'].nunique()}")
print(f"  Years: {df['fyear'].min()}–{df['fyear'].max()}")

# ── Save ──────────────────────────────────────────────────────────────────────
df.to_parquet(OUT_PATH, index=False)

LOG_PATH.write_text(
    f"Clean log\n"
    f"Raw observations: {n_raw}\n"
    f"Clean observations: {len(df)}\n"
    f"Firms: {df['gvkey'].nunique()}\n"
    f"Countries: {df['loc'].nunique()}\n"
    f"Years: {df['fyear'].min()}–{df['fyear'].max()}\n"
)

print(f"\nSaved cleaned panel to {OUT_PATH}")
print(f"Saved clean log to {LOG_PATH}")