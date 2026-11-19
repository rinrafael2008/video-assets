"""Predict UPCOMING club matches and compare with odds YOU typed in (e.g. from Stoiximan).

    python -m footy.upcoming my_fixtures.csv

Why typed in by hand? Betting sites and score apps (Stoiximan, Flashscore, ...) don't
give permission to copy their data automatically, so this project does not scrape them.
Reading the odds in the app and typing them into a CSV for your own research is fine.

The CSV (copy fixtures_template.csv) has one row per match:
    Division, MatchDate, HomeTeam, AwayTeam, OddHome, OddDraw, OddAway, Bookmaker
    (optional: FTHome, FTAway)
* Rows WITHOUT a score are upcoming matches -> they get predictions.
* Rows WITH a score (FTHome, FTAway) are recent results you add yourself; they update
  the Elo ratings and form. Use this to fill the gap between the end of the dataset and today.

Output: outputs/upcoming_predictions.csv. This is research only. In every backtest we ran,
the model did not beat the bookmaker, so a "disagreement" here is NOT a reason to bet.
"""
from __future__ import annotations

import argparse
import difflib
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from footy import config, data
from footy.features import build_features
from footy.models import GoalsModel, SklearnOutcomeModel
from footy.odds import overround, remove_margin_proportional

ODDS = ["OddHome", "OddDraw", "OddAway"]
REQUIRED = ["Division", "MatchDate", "HomeTeam", "AwayTeam"]
STALE_DAYS = 21


def divisions_for(divs) -> list[str]:
    """Load the whole country group (e.g. E0 -> E0+E1) so ratings follow promoted teams."""
    out = set(divs)
    for group in config.LEAGUE_GROUPS.values():
        if out & set(group):
            out |= set(group)
    return sorted(out)


def fix_capitalisation(fixtures, known_teams, warnings) -> None:
    """'paok' or 'PAOK ' -> 'PAOK' (only when the match is unambiguous)."""
    lookup = {}
    for t in known_teams:
        lookup.setdefault(t.lower(), []).append(t)
    for col in ("HomeTeam", "AwayTeam"):
        for team in fixtures[col].unique():
            hits = lookup.get(str(team).strip().lower(), [])
            if team not in known_teams and len(hits) == 1:
                fixtures.loc[fixtures[col] == team, col] = hits[0]
                warnings.append(f"Read team '{team}' as '{hits[0]}'.")


def check_team_names(fixtures, known_teams) -> list[str]:
    problems = []
    for team in sorted(set(fixtures.HomeTeam) | set(fixtures.AwayTeam)):
        if team not in known_teams:
            close = difflib.get_close_matches(team, known_teams, n=3, cutoff=0.5)
            problems.append(f"Unknown team '{team}'." + (f" Did you mean: {', '.join(close)}?" if close else ""))
    return problems


def predict(history_raw: pd.DataFrame, fixtures: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Return (predictions for score-less fixture rows, list of warnings)."""
    missing = [c for c in REQUIRED if c not in fixtures.columns]
    if missing:
        raise ValueError(f"Fixture file is missing columns: {missing}")
    fx = fixtures.copy()
    for c in ODDS + ["FTHome", "FTAway", "Over25", "Under25"]:
        fx[c] = pd.to_numeric(fx[c], errors="coerce") if c in fx else np.nan
    fx["MatchDate"] = pd.to_datetime(fx["MatchDate"])
    fx["Bookmaker"] = fx["Bookmaker"] if "Bookmaker" in fx else ""

    history = data.clean(history_raw, divisions_for(fx.Division.unique()))
    known = sorted(set(history.HomeTeam) | set(history.AwayTeam))
    warnings = []
    fix_capitalisation(fx, known, warnings)
    problems = check_team_names(fx, known)
    if problems:
        raise ValueError("\n".join(problems))
    if (fx.MatchDate < history.MatchDate.max()).any():
        warnings.append("Some of your rows are dated before the end of the dataset; they are added after it anyway.")
    last_known = max(history.MatchDate.max(), fx.loc[fx.FTHome.notna(), "MatchDate"].max()
                     if fx.FTHome.notna().any() else history.MatchDate.max())
    upcoming_dates = fx.loc[fx.FTHome.isna(), "MatchDate"]
    gap = (upcoming_dates.min() - last_known).days if len(upcoming_dates) else 0
    if gap > STALE_DAYS:
        warnings.append(f"The latest known result is from {last_known:%Y-%m-%d}, {gap} days before your first "
                        "upcoming match. Ratings miss recent results: add them as rows with FTHome/FTAway.")

    fx["FTResult"] = np.where(fx.FTHome.isna(), None,
                              np.select([fx.FTHome > fx.FTAway, fx.FTHome == fx.FTAway], ["H", "D"], "A"))
    fx["Season"] = data.season_of(fx["MatchDate"])
    fx["_fixture"] = True
    combined = pd.concat([history.assign(_fixture=False), fx], ignore_index=True)
    combined = combined.sort_values("MatchDate", kind="stable").reset_index(drop=True)
    feats = build_features(combined)

    train = feats[~feats._fixture & feats.FTResult.notna()]
    train = train[train.Season > train.Season.min()]             # skip the Elo burn-in season
    upcoming = feats[feats._fixture & feats.FTHome.isna()].copy()
    if upcoming.empty:
        raise ValueError("No upcoming matches found (every row has a score).")

    model = SklearnOutcomeModel("Logistic regression (C=0.1)", LogisticRegression(C=0.1, max_iter=2000)).fit(train)
    p = model.predict_proba(upcoming)
    g = GoalsModel().fit(train).predict(upcoming)

    out = upcoming[["Division", "MatchDate", "HomeTeam", "AwayTeam", "Bookmaker", *ODDS]].reset_index(drop=True)
    out[["model_pH", "model_pD", "model_pA"]] = p
    out[["model_fair_oddH", "model_fair_oddD", "model_fair_oddA"]] = 1 / p
    odds = out[ODDS].to_numpy(float)
    out["bookmaker_margin"] = overround(odds) - 1
    with np.errstate(invalid="ignore"):
        out[["book_pH", "book_pD", "book_pA"]] = remove_margin_proportional(odds)
        ev = p * odds - 1
    out[["ev_H", "ev_D", "ev_A"]] = ev
    out["exp_home_goals"], out["exp_away_goals"], out["p_over25"] = (
        g["exp_home_goals"], g["exp_away_goals"], g["p_over25"])
    best = np.nanargmax(np.where(np.isnan(ev), -np.inf, ev), axis=1)
    biggest = ev[np.arange(len(ev)), best]
    out["research_note"] = np.where(
        np.isnan(biggest), "no odds entered",
        np.where(biggest > 0, [f"model rates {'HDA'[b]} higher than the bookmaker (not a bet signal)" for b in best],
                 "model agrees with or is below the bookmaker on every outcome"))
    return out, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fixtures_csv", help="your fixture/odds file (see fixtures_template.csv)")
    args = parser.parse_args()
    try:
        out, warnings = predict(data.load_raw(), pd.read_csv(args.fixtures_csv))
    except ValueError as e:
        sys.exit(f"Problem with your file:\n{e}")
    for w in warnings:
        print("WARNING:", w)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(config.OUTPUT_DIR / "upcoming_predictions.csv", index=False)
    cols = ["HomeTeam", "AwayTeam", "model_pH", "model_pD", "model_pA", "book_pH", "book_pD", "book_pA"]
    print(out[cols].round(3).to_string(index=False))
    print(f"\nSaved {config.OUTPUT_DIR / 'upcoming_predictions.csv'} (research only - never place real bets based on this).")


if __name__ == "__main__":
    main()
