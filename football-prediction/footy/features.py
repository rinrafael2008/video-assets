"""Step 2b: build features using ONLY information available before kickoff.

We walk through the matches in date order. For each match we:
  1. read the current Elo ratings and recent form of both teams  -> features
  2. only THEN look at the result and update ratings / form       -> no peeking

Because step 1 always happens before step 2, a match's own result (and any later
result) can never leak into its features. tests/test_no_leakage.py checks this.

Rows without a score (future fixtures) get features but do not update anything,
which is how we predict upcoming matches.
"""
from __future__ import annotations

from collections import defaultdict, deque

import numpy as np
import pandas as pd

from footy import config
from footy.elo import Elo

FORM_WINDOW = 5
SHOTS_WINDOW = 8          # shots are noisy per game, so average over more matches
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
    # Moved division this season (known before the season starts): 1 = yes, 0 = no.
    "home_promoted", "away_promoted", "home_relegated", "away_relegated",
    # Shots: a better sign of how well a team really plays than goals, which are partly luck.
    # Averages over each team's previous 8 matches (missing in leagues/seasons without shot data).
    "home_shots_for", "home_shots_against", "home_sot_for", "home_sot_against",
    "away_shots_for", "away_shots_against", "away_sot_for", "away_sot_against",
]
SHOT_COLUMNS = FEATURE_COLUMNS[-8:]


def tier(division: str) -> int:
    return 1 if division in config.TOP_DIVISIONS else 2


def build_features(matches: pd.DataFrame, elo: Elo | None = None, only_elo: bool = False) -> pd.DataFrame:
    """Return a copy of `matches` with FEATURE_COLUMNS added (one row per match).
    only_elo=True computes just the Elo columns (fast; used to tune the Elo settings)."""
    elo = elo or Elo()
    team_season: dict[str, tuple[int, str]] = {}   # team -> (season, division) of its latest match
    moved: dict[str, int] = {}                      # team -> +1 promoted / -1 relegated / 0 this season
    history = defaultdict(lambda: deque(maxlen=FORM_WINDOW))  # team -> (points, gf, ga)
    shots = defaultdict(lambda: deque(maxlen=SHOTS_WINDOW))   # team -> (shots for/against, on target for/against)
    games_played = defaultdict(int)
    last_date: dict[str, pd.Timestamp] = {}
    rows = []
    current_season = None

    for m in matches.itertuples(index=False):
        if m.Season != current_season:
            if current_season is not None:
                elo.new_season()
            current_season = m.Season

        # Promotion / relegation: decided at a team's first match of a season, by comparing its
        # division with last season's. Known before the season starts, so no leakage.
        for team in (m.HomeTeam, m.AwayTeam):
            last = team_season.get(team)
            if last is None or last[0] != m.Season:
                change = 0 if last is None else (tier(last[1]) - tier(m.Division))   # +1 up, -1 down
                if change:
                    elo.change_division(team, promoted=change > 0)
                moved[team] = change
                team_season[team] = (m.Season, m.Division)

        # ---- 1. features: read state BEFORE the match --------------------------
        f = {}
        eh, ea = elo.rating(m.HomeTeam), elo.rating(m.AwayTeam)
        f["elo_home"], f["elo_away"] = eh, ea
        f["elo_diff"] = eh + elo.home_advantage - ea
        if only_elo:
            rows.append(f)
            if not (pd.isna(m.FTHome) or pd.isna(m.FTAway)):
                elo.update(m.HomeTeam, m.AwayTeam, int(m.FTHome), int(m.FTAway))
            continue
        for side, team in (("home", m.HomeTeam), ("away", m.AwayTeam)):
            f[f"{side}_promoted"] = float(moved.get(team, 0) > 0)
            f[f"{side}_relegated"] = float(moved.get(team, 0) < 0)
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
            known = [x for x in shots[team] if not np.isnan(x).any()]
            avg = np.mean(known, axis=0) if known else [np.nan] * 4
            (f[f"{side}_shots_for"], f[f"{side}_shots_against"],
             f[f"{side}_sot_for"], f[f"{side}_sot_against"]) = avg
        f["is_top_division"] = float(m.Division in config.TOP_DIVISIONS)
        rows.append(f)

        # ---- 2. update state AFTER the match ------------------------------------
        if pd.isna(m.FTHome) or pd.isna(m.FTAway):
            continue                       # future fixture: nothing to learn yet
        hg, ag = int(m.FTHome), int(m.FTAway)
        hp = 3 if hg > ag else (1 if hg == ag else 0)
        ap = 3 if ag > hg else (1 if hg == ag else 0)
        history[m.HomeTeam].append((hp, hg, ag))
        history[m.AwayTeam].append((ap, ag, hg))
        hs, as_, ht, at = (float(getattr(m, c, np.nan)) for c in ("HomeShots", "AwayShots", "HomeTarget", "AwayTarget"))
        shots[m.HomeTeam].append(np.array([hs, as_, ht, at]))
        shots[m.AwayTeam].append(np.array([as_, hs, at, ht]))
        games_played[m.HomeTeam] += 1
        games_played[m.AwayTeam] += 1
        last_date[m.HomeTeam] = last_date[m.AwayTeam] = m.MatchDate
        elo.update(m.HomeTeam, m.AwayTeam, hg, ag)

    cols = ["elo_diff", "elo_home", "elo_away"] if only_elo else FEATURE_COLUMNS
    feats = pd.DataFrame(rows, index=matches.index)[cols]
    return pd.concat([matches, feats], axis=1)
