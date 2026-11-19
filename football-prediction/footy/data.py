"""Step 1: download and clean the historical match data.

Run:  python -m footy.data      (downloads data/Matches.csv, ~45 MB)
"""
from __future__ import annotations

import sys
import urllib.request

import numpy as np
import pandas as pd

from footy import config

# Only columns that are known BEFORE kickoff (odds) or that we need as the answer (goals).
# We deliberately ignore shots, cards, corners, half-time scores and the dataset's
# "cluster" columns: those describe the match itself, so using them would be cheating
# (data leakage). We also recompute Elo and form ourselves, so we know exactly how
# they were built and that they only use earlier matches.
KEEP_COLUMNS = [
    "Division", "MatchDate", "MatchTime", "HomeTeam", "AwayTeam",
    "FTHome", "FTAway", "FTResult",
    "OddHome", "OddDraw", "OddAway",     # Bet365 1X2 odds (one real bookmaker)
    "MaxHome", "MaxDraw", "MaxAway",     # best price across ~17 bookmakers (optimistic)
    "Over25", "Under25",                 # Bet365 over/under 2.5 goals odds
]
ODDS_TRIPLES = [("OddHome", "OddDraw", "OddAway"), ("MaxHome", "MaxDraw", "MaxAway")]


def download(url: str = config.DATA_URL, dest=config.MATCHES_CSV) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url}\n  -> {dest} (about 45 MB, please wait)...")
    urllib.request.urlretrieve(url, dest)
    print("Done.")


def season_of(dates: pd.Series) -> pd.Series:
    """A season starts in July: 2023-08-12 -> 2023 (2023/24), 2024-03-01 -> 2023."""
    return np.where(dates.dt.month >= 7, dates.dt.year, dates.dt.year - 1).astype(int)


def clean(raw: pd.DataFrame, divisions=None) -> pd.DataFrame:
    divisions = divisions or config.DIVISIONS
    df = raw.loc[raw["Division"].isin(divisions), KEEP_COLUMNS].copy()
    df["MatchDate"] = pd.to_datetime(df["MatchDate"])
    df = df.dropna(subset=["FTHome", "FTAway"])           # need the final score
    df["FTHome"] = df["FTHome"].astype(int)
    df["FTAway"] = df["FTAway"].astype(int)
    df["FTResult"] = np.select(
        [df.FTHome > df.FTAway, df.FTHome == df.FTAway], ["H", "D"], "A")

    # Odds sanity checks: decimal odds must be > 1, and the three implied
    # probabilities of a 1X2 market should add up to a bit more than 1 (the margin).
    odds_cols = [c for t in ODDS_TRIPLES for c in t] + ["Over25", "Under25"]
    for c in odds_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df.loc[df[c] <= 1.0, c] = np.nan
    for triple in ODDS_TRIPLES:
        booksum = (1.0 / df[list(triple)]).sum(axis=1, min_count=3)
        bad = ~booksum.between(0.97, 1.30)   # Max odds can sum slightly below 1
        df.loc[bad, list(triple)] = np.nan
    ou = 1 / df["Over25"] + 1 / df["Under25"]
    df.loc[~ou.between(1.0, 1.25), ["Over25", "Under25"]] = np.nan

    df["Season"] = season_of(df["MatchDate"])
    # Chronological order. Time can be missing; ties keep the file order.
    df["_order"] = np.arange(len(df))
    df = df.sort_values(["MatchDate", "MatchTime", "_order"], na_position="first", kind="stable")
    df = df.drop(columns="_order").reset_index(drop=True)
    df = df.drop_duplicates(["MatchDate", "HomeTeam", "AwayTeam"])
    return df.reset_index(drop=True)


def load_raw(path=config.MATCHES_CSV) -> pd.DataFrame:
    if not path.exists():
        sys.exit(f"Data file not found: {path}\nRun first:  python -m footy.data")
    return pd.read_csv(path, low_memory=False)


def load(path=config.MATCHES_CSV, divisions=None) -> pd.DataFrame:
    return clean(load_raw(path), divisions)


if __name__ == "__main__":
    download()
