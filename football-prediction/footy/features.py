"""Step 2b: build features using ONLY information available before kickoff.

We walk through the matches in date order. For each match we:
  1. read the current Elo ratings and recent form of both teams  -> features
  2. only THEN look at the result and update ratings / form       -> no peeking

Because step 1 always happens before step 2, a match's own result (and any later
result) can never leak into its features. tests/test_no_leakage.py checks this.
"""
from __future__ import annotations

from collections import defaultdict, deque

import numpy as np
import pandas as pd

from footy.elo import Elo

FORM_WINDOW = 5
MAX_REST_DAYS = 30

FEATURE_COLUMNS = [
    "elo_diff",          # home rating + home advantage - away rating
    "elo_home", "elo_away",
    "home_pts_avg", "away_pts_avg",      # points per game, last 5 matches
    "home_gf_avg", "home_ga_avg",        # goals for / against per game, last 5
    "away_gf_avg", "away_ga_avg",
    "home_rest_days", "away_rest_days",
    "home_games_played", "away_games_played",  # how much history we have (capped at 10)
    "is_top_division",
]


def build_features(matches: pd.DataFrame, elo: Elo | None = None) -> pd.DataFrame:
    """Return a copy of `matches` with FEATURE_COLUMNS added (one row per match)."""
    elo = elo or Elo()
    history = defaultdict(lambda: deque(maxlen=FORM_WINDOW))  # team -> (points, gf, ga)
    games_played = defaultdict(int)
    last_date: dict[str, pd.Timestamp] = {}
    rows = []
    current_season = None

    for m in matches.itertuples(index=False):
        if m.Season != current_season:
            if current_season is not None:
                elo.new_season()
            current_season = m.Season

        # ---- 1. features: read state BEFORE the match --------------------------
        f = {}
        eh, ea = elo.rating(m.HomeTeam), elo.rating(m.AwayTeam)
        f["elo_home"], f["elo_away"] = eh, ea
        f["elo_diff"] = eh + elo.home_advantage - ea
        for side, team in (("home", m.HomeTeam), ("away", m.AwayTeam)):
            h = history[team]
            if h:
                arr = np.array(h, dtype=float)
                f[f"{side}_pts_avg"], f[f"{side}_gf_avg"], f[f"{side}_ga_avg"] = arr.mean(axis=0)
            else:  # no history yet: leave missing, the model's imputer fills it in
                f[f"{side}_pts_avg"] = f[f"{side}_gf_avg"] = f[f"{side}_ga_avg"] = np.nan
            if team in last_date:
                f[f"{side}_rest_days"] = min((m.MatchDate - last_date[team]).days, MAX_REST_DAYS)
            else:
                f[f"{side}_rest_days"] = MAX_REST_DAYS
            f[f"{side}_games_played"] = min(games_played[team], 10)
        f["is_top_division"] = float(m.Division in ("E0", "SP1", "D1", "I1", "F1"))
        rows.append(f)

        # ---- 2. update state AFTER the match ------------------------------------
        hg, ag = m.FTHome, m.FTAway
        hp = 3 if hg > ag else (1 if hg == ag else 0)
        ap = 3 if ag > hg else (1 if hg == ag else 0)
        history[m.HomeTeam].append((hp, hg, ag))
        history[m.AwayTeam].append((ap, ag, hg))
        games_played[m.HomeTeam] += 1
        games_played[m.AwayTeam] += 1
        last_date[m.HomeTeam] = last_date[m.AwayTeam] = m.MatchDate
        elo.update(m.HomeTeam, m.AwayTeam, hg, ag)

    feats = pd.DataFrame(rows, index=matches.index)[FEATURE_COLUMNS]
    return pd.concat([matches, feats], axis=1)
