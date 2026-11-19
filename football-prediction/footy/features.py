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
    # Match importance, from the league table BEFORE this match (see table_context below).
    "season_progress",
    "home_table_pos", "away_table_pos",           # 0 = top, 1 = bottom
    "home_title_gap", "away_title_gap",           # points behind the leader / points still available
    "home_drop_margin", "away_drop_margin",       # points above the relegation zone / points still available
    "home_nothing_to_play", "away_nothing_to_play",  # late in season, can't reach the top, can't go down
    # Shots: a better sign of how well a team really plays than goals, which are partly luck.
    # Averages over each team's previous 8 matches (missing in leagues/seasons without shot data).
    "home_shots_for", "home_shots_against", "home_sot_for", "home_sot_against",
    "away_shots_for", "away_shots_against", "away_sot_for", "away_sot_against",
]
SHOT_COLUMNS = FEATURE_COLUMNS[-8:]
CONTEXT_COLUMNS = ["season_progress", "home_table_pos", "away_table_pos", "home_title_gap", "away_title_gap",
                   "home_drop_margin", "away_drop_margin", "home_nothing_to_play", "away_nothing_to_play"]
RELEGATION_PLACES = 3   # bottom 3 go down (2 in some leagues; close enough for a "danger" measure)


def table_context(table: dict, team: str, n_teams: int, games_total: int | None = None) -> dict:
    """Where `team` stands in its league table, and how much is still at stake.
    table: team -> [points, played, goal difference], from matches BEFORE this one."""
    rows = sorted(((v[0], v[2], t) for t, v in table.items()), reverse=True)
    order = [t for _, _, t in rows]
    pts, played, _ = table.get(team, [0, 0, 0])
    # games_total: league matches per team this season (Scotland: 38 with 12 teams; Belgium has
    # play-offs). Defaults to a plain double round-robin.
    games_total = max(games_total or 2 * (n_teams - 1), played, 1)
    left = max(games_total - played, 0)
    available = 3 * left + 1                                   # +1 avoids dividing by zero at the end
    leader = rows[0][0] if rows else 0
    line = max(n_teams - RELEGATION_PLACES, 0)                  # first place in the relegation zone
    drop_line = rows[line][0] if line < len(rows) else 0
    pos = order.index(team) if team in order else len(order)
    title_gap = min((leader - pts) / available, 3.0)             # capped: beyond 3 it's "impossible" anyway
    drop_margin = float(np.clip((pts - drop_line) / available, -3.0, 3.0))
    return {"table_pos": pos / max(n_teams - 1, 1), "title_gap": title_gap, "drop_margin": drop_margin,
            "nothing_to_play": float(played / games_total > 0.7 and title_gap > 1 and drop_margin > 1),
            "progress": played / games_total}


def tier(division: str) -> int:
    return 1 if division in config.TOP_DIVISIONS else 2


def build_features(matches: pd.DataFrame, elo: Elo | None = None, only_elo: bool = False) -> pd.DataFrame:
    """Return a copy of `matches` with FEATURE_COLUMNS added (one row per match).
    only_elo=True computes just the Elo columns (fast; used to tune the Elo settings)."""
    elo = elo or Elo()
    team_season: dict[str, tuple[int, str]] = {}   # team -> (season, division) of its latest match
    tables = defaultdict(dict)                      # (division, season) -> team -> [points, played, goal diff]
    # Number of teams per league-season: known before the season (the fixture list is published).
    # League format (teams, league matches per team), taken from the PREVIOUS season of the same
    # league so nothing from the future is used. Scotland: 12 teams, 38 matches; Belgium: play-offs.
    season_format = {}
    for k, g in matches.groupby(["Division", "Season"]):
        season_format[k] = (len(set(g.HomeTeam) | set(g.AwayTeam)),
                            int(pd.concat([g.HomeTeam, g.AwayTeam]).value_counts().max()))
    teams_seen = defaultdict(set)                   # fallback for a league's first season
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
        key = (m.Division, m.Season)
        teams_seen[key] |= {m.HomeTeam, m.AwayTeam}
        n_teams, games_total = season_format.get((m.Division, m.Season - 1), (len(teams_seen[key]), None))
        progress = []
        for side, team in (("home", m.HomeTeam), ("away", m.AwayTeam)):
            c = table_context(tables[key], team, max(n_teams, 2), games_total)
            for k in ("table_pos", "title_gap", "drop_margin", "nothing_to_play"):
                f[f"{side}_{k}"] = c[k]
            progress.append(c["progress"])
        f["season_progress"] = float(np.mean(progress))
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
        t = tables[(m.Division, m.Season)]
        for team, pts, gd in ((m.HomeTeam, hp, hg - ag), (m.AwayTeam, ap, ag - hg)):
            row = t.setdefault(team, [0, 0, 0])
            row[0] += pts
            row[1] += 1
            row[2] += gd

    cols = ["elo_diff", "elo_home", "elo_away"] if only_elo else FEATURE_COLUMNS
    feats = pd.DataFrame(rows, index=matches.index)[cols]
    return pd.concat([matches, feats], axis=1)
