"""National teams: same ideas as the club pipeline, adapted for international football.

    python -m footy.international --download    (first time: get the data, ~4 MB)
    python -m footy.international

Differences from club football:
* Many matches are at a NEUTRAL venue (e.g. World Cup) -> no home advantage there.
* Matches differ in importance: a World Cup match moves Elo ratings more than a friendly.
* There are no seasons; we split by date.
* This free dataset has NO betting odds, so there is no bookmaker comparison and no
  backtest for national teams. We only measure how good the probabilities are.
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from collections import defaultdict, deque

import numpy as np
import pandas as pd

from footy import config, evaluate as ev
from footy.elo import Elo
from footy.models import EloBaseline, GoalsModel, candidate_outcome_models, outcome_index

INTL_FEATURES = [
    "elo_diff", "elo_home", "elo_away", "neutral", "importance",
    "home_pts_avg", "away_pts_avg", "home_gf_avg", "home_ga_avg", "away_gf_avg", "away_ga_avg",
    "home_rest_days", "away_rest_days", "home_games_played", "away_games_played",
]
MAX_REST_DAYS = 365

MAJOR_FINALS = {"FIFA World Cup"}
CONTINENTAL_FINALS = {"UEFA Euro", "Copa América", "African Cup of Nations", "AFC Asian Cup",
                      "Gold Cup", "Confederations Cup", "Oceania Nations Cup"}


def importance_k(tournament: str) -> float:
    """Elo K-factor by match importance (similar to eloratings.net)."""
    if tournament in MAJOR_FINALS:
        return 60.0
    if tournament in CONTINENTAL_FINALS:
        return 50.0
    if "qualification" in tournament or "Nations League" in tournament:
        return 40.0
    if tournament == "Friendly":
        return 20.0
    return 30.0


def goal_difference_multiplier(home_goals: int, away_goals: int) -> float:
    """Big wins move ratings more: 1-goal win x1, 2 goals x1.5, 3+ goals x(11+N)/8."""
    n = abs(home_goals - away_goals)
    return 1.0 if n <= 1 else (1.5 if n == 2 else (11 + n) / 8)


def download(url=config.INTL_DATA_URL, dest=config.INTL_CSV):
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url}\n  -> {dest}")
    urllib.request.urlretrieve(url, dest)


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns={"date": "MatchDate", "home_team": "HomeTeam", "away_team": "AwayTeam",
                             "home_score": "FTHome", "away_score": "FTAway", "tournament": "Tournament"})
    df["MatchDate"] = pd.to_datetime(df["MatchDate"])
    df["neutral"] = df["neutral"].astype(str).str.upper().eq("TRUE").astype(float)
    df["FTHome"] = pd.to_numeric(df["FTHome"], errors="coerce")
    df["FTAway"] = pd.to_numeric(df["FTAway"], errors="coerce")
    df["FTResult"] = np.select([df.FTHome > df.FTAway, df.FTHome == df.FTAway], ["H", "D"], "A")
    df.loc[df.FTHome.isna() | df.FTAway.isna(), "FTResult"] = None
    df = df.sort_values("MatchDate", kind="stable").reset_index(drop=True)
    return df[["MatchDate", "HomeTeam", "AwayTeam", "FTHome", "FTAway", "FTResult", "Tournament", "neutral"]]


def build_features(matches: pd.DataFrame, elo: Elo | None = None) -> pd.DataFrame:
    """Same rule as the club version: read features BEFORE the match, update AFTER."""
    elo = elo or Elo(home_advantage=config.INTL_HOME_ADVANTAGE, season_regression=0.0)
    history = defaultdict(lambda: deque(maxlen=5))
    games_played = defaultdict(int)
    last_date = {}
    rows = []
    for m in matches.itertuples(index=False):
        neutral = bool(m.neutral)
        eh, ea = elo.rating(m.HomeTeam), elo.rating(m.AwayTeam)
        f = {"elo_home": eh, "elo_away": ea, "elo_diff": eh + elo.home_edge(neutral) - ea,
             "importance": importance_k(m.Tournament)}   # "neutral" is already a column
        for side, team in (("home", m.HomeTeam), ("away", m.AwayTeam)):
            h = history[team]
            if h:
                f[f"{side}_pts_avg"], f[f"{side}_gf_avg"], f[f"{side}_ga_avg"] = np.mean(np.array(h, float), axis=0)
            else:
                f[f"{side}_pts_avg"] = f[f"{side}_gf_avg"] = f[f"{side}_ga_avg"] = np.nan
            f[f"{side}_rest_days"] = (min((m.MatchDate - last_date[team]).days, MAX_REST_DAYS)
                                      if team in last_date else MAX_REST_DAYS)
            f[f"{side}_games_played"] = min(games_played[team], 10)
        rows.append(f)

        if pd.isna(m.FTHome) or pd.isna(m.FTAway):
            continue
        hg, ag = int(m.FTHome), int(m.FTAway)
        hp, ap = (3, 0) if hg > ag else ((1, 1) if hg == ag else (0, 3))
        history[m.HomeTeam].append((hp, hg, ag))
        history[m.AwayTeam].append((ap, ag, hg))
        for t in (m.HomeTeam, m.AwayTeam):
            games_played[t] += 1
            last_date[t] = m.MatchDate
        elo.update(m.HomeTeam, m.AwayTeam, hg, ag,
                   k=importance_k(m.Tournament) * goal_difference_multiplier(hg, ag), neutral=neutral)
    return pd.concat([matches, pd.DataFrame(rows, index=matches.index)[[c for c in INTL_FEATURES if c != "neutral"]]], axis=1)


def date_split(df, train_start=config.INTL_TRAIN_START, train_end=config.INTL_TRAIN_END,
               valid_end=config.INTL_VALID_END):
    df = df[df.FTResult.notna()]
    train = df[(df.MatchDate >= train_start) & (df.MatchDate <= train_end)]
    valid = df[(df.MatchDate > train_end) & (df.MatchDate <= valid_end)]
    test = df[df.MatchDate > valid_end]
    assert train.MatchDate.max() < valid.MatchDate.min() <= valid.MatchDate.max() < test.MatchDate.min()
    return train.copy(), valid.copy(), test.copy()


def run(matches: pd.DataFrame, out_dir=config.OUTPUT_DIR / "international", verbose=True, **split_kw) -> dict:
    say = print if verbose else (lambda *a, **k: None)
    out_dir.mkdir(parents=True, exist_ok=True)
    say("Building pre-match features for national teams...")
    df = build_features(matches)
    train, valid, test = date_split(df, **split_kw)
    say(f"    train {len(train):,} | validation {len(valid):,} | test {len(test):,} matches")
    y_tr, y_va, y_te = (outcome_index(d.FTResult) for d in (train, valid, test))

    candidates = [EloBaseline()] + candidate_outcome_models(INTL_FEATURES)
    vrows = []
    for m in candidates:
        m.fit(train)
        vrows.append({"model": m.name, **ev.outcome_metrics(m.predict_proba(valid), y_va)})
    valid_table = pd.DataFrame(vrows)
    best_name = min(candidates[1:], key=lambda m: valid_table.set_index("model").log_loss[m.name]).name
    say(valid_table[["model", "log_loss", "brier", "accuracy"]].round(4).to_string(index=False))

    trval = pd.concat([train, valid])
    elo_model = EloBaseline().fit(trval)
    ml_model = [m for m in candidate_outcome_models(INTL_FEATURES) if m.name == best_name][0].fit(trval)
    goals_model = GoalsModel(features=INTL_FEATURES).fit(trval)
    p_elo, p_ml = elo_model.predict_proba(test), ml_model.predict_proba(test)
    goals = goals_model.predict(test)
    base = np.bincount(outcome_index(trval.FTResult), minlength=3) / len(trval)

    trows = []
    for name, p in [("Elo baseline", p_elo), (best_name, p_ml),
                    ("Poisson goals model (H/D/A)", np.c_[goals["p_home_poisson"], goals["p_draw_poisson"],
                                                          goals["p_away_poisson"]]),
                    ("Naive (historical H/D/A rates)", np.tile(base, (len(test), 1)))]:
        trows.append({"model": name, "subset": "all test matches", **ev.outcome_metrics(p, y_te)})
        for label, mask in [("competitive matches", test.Tournament.ne("Friendly").to_numpy()),
                            ("major tournament finals", test.Tournament.isin(MAJOR_FINALS | CONTINENTAL_FINALS).to_numpy())]:
            if mask.sum():
                trows.append({"model": name, "subset": label, **ev.outcome_metrics(p[mask], y_te[mask])})
    test_table = pd.DataFrame(trows)
    say(test_table[test_table.subset == "all test matches"][["model", "log_loss", "brier", "accuracy",
                                                             "calibration_error"]].round(4).to_string(index=False))

    preds = test[["MatchDate", "HomeTeam", "AwayTeam", "FTHome", "FTAway", "FTResult", "Tournament", "neutral"]].copy()
    preds[["elo_pH", "elo_pD", "elo_pA"]] = p_elo
    preds[["ml_pH", "ml_pD", "ml_pA"]] = p_ml
    preds["exp_home_goals"], preds["exp_away_goals"], preds["p_over25"] = (
        goals["exp_home_goals"], goals["exp_away_goals"], goals["p_over25"])
    preds.to_csv(out_dir / "test_predictions.csv", index=False)
    pd.concat([ev.calibration_table(p_elo, y_te).assign(model="Elo baseline"),
               ev.calibration_table(p_ml, y_te).assign(model=best_name)]).to_csv(out_dir / "calibration.csv", index=False)
    valid_table.to_csv(out_dir / "validation_metrics.csv", index=False)
    test_table.to_csv(out_dir / "test_metrics.csv", index=False)
    for stale in ("test_backtest.csv", "validation_backtest.csv", "test_bets.csv"):
        (out_dir / stale).unlink(missing_ok=True)

    summary = {
        "divisions": ["International (national teams)"],
        "train_seasons": [train.MatchDate.min().year, train.MatchDate.max().year],
        "valid_seasons": [valid.MatchDate.min().year, valid.MatchDate.max().year],
        "test_seasons": [test.MatchDate.min().year, test.MatchDate.max().year],
        "n_train": len(train), "n_valid": len(valid), "n_test": len(test), "n_test_with_odds": 0,
        "best_ml_model": best_name, "chosen_threshold": None,
        "recommendation": "No odds in this dataset: no bookmaker comparison or backtest for national teams.",
        "goals": {
            "mae_home_goals_model": float(np.mean(np.abs(goals["exp_home_goals"] - test.FTHome))),
            "mae_away_goals_model": float(np.mean(np.abs(goals["exp_away_goals"] - test.FTAway))),
            "mae_home_goals_naive": float(np.mean(np.abs(trval.FTHome.mean() - test.FTHome))),
            "mae_away_goals_naive": float(np.mean(np.abs(trval.FTAway.mean() - test.FTAway))),
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    say(f"Done. Results in {out_dir}")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--download", action="store_true", help="download the dataset first")
    args = parser.parse_args()
    if args.download or not config.INTL_CSV.exists():
        download()
    run(clean(pd.read_csv(config.INTL_CSV)))


if __name__ == "__main__":
    main()
