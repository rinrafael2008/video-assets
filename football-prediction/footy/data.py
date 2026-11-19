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


def unify_team_spellings(df: pd.DataFrame) -> pd.DataFrame:
    """The dataset sometimes spells one club two ways ("Nott'm Forest" / "Nottm Forest").
    Two spellings that differ only in punctuation, spaces or capitals are the same club,
    so we rename all of them to the most common spelling. Otherwise Elo would treat
    them as two different teams."""
    names = pd.concat([df.HomeTeam, df.AwayTeam]).value_counts()
    key = names.index.str.lower().str.replace(r"[^a-z0-9]", "", regex=True)
    canonical = {}
    for k, group in pd.Series(names.index, index=key).groupby(level=0):
        best = group.iloc[0]                        # value_counts order: most common first
        canonical.update({name: best for name in group})
    df["HomeTeam"] = df.HomeTeam.map(canonical)
    df["AwayTeam"] = df.AwayTeam.map(canonical)
    return df


def clean(raw: pd.DataFrame, divisions=None) -> pd.DataFrame:
    divisions = divisions or config.DIVISIONS
    df = raw.loc[raw["Division"].isin(divisions), KEEP_COLUMNS].copy()
    df["MatchDate"] = pd.to_datetime(df["MatchDate"])
    df = df.dropna(subset=["FTHome", "FTAway"])           # need the final score
    df = unify_team_spellings(df)
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


UPDATE_CSV = config.DATA_DIR / "Matches_update.csv"


def load_raw(path=config.MATCHES_CSV, update_path=UPDATE_CSV) -> pd.DataFrame:
    """The main dataset, plus the extra matches from `python -m footy.update` if you ran it."""
    if not path.exists():
        sys.exit(f"Data file not found: {path}\nRun first:  python -m footy.data")
    raw = pd.read_csv(path, low_memory=False)
    if update_path is not None and update_path.exists():
        extra = pd.read_csv(update_path, low_memory=False)
        raw = pd.concat([raw, extra[[c for c in extra.columns if c in raw.columns]]], ignore_index=True)
    return raw


def load(path=config.MATCHES_CSV, divisions=None) -> pd.DataFrame:
    return clean(load_raw(path), divisions)


if __name__ == "__main__":
    download()
