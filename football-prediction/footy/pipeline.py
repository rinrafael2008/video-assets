"""Run the whole research pipeline end to end and write results to outputs/.

    python -m footy.pipeline

Steps: load data -> features -> split -> train models -> pick best on validation
-> refit on train+validation -> evaluate ONCE on test -> compare with bookmaker
-> hypothetical backtest -> save files for the dashboard.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from footy import backtest as bt
from footy import config, data, evaluate as ev
from footy.features import build_features
from footy.models import EloBaseline, GoalsModel, candidate_outcome_models, outcome_index
from footy.odds import overround, remove_margin_power, remove_margin_proportional
from footy.split import chronological_split

BET365 = ["OddHome", "OddDraw", "OddAway"]
MAXODDS = ["MaxHome", "MaxDraw", "MaxAway"]


def market_probs(df, cols=BET365, method="proportional"):
    f = remove_margin_proportional if method == "proportional" else remove_margin_power
    return f(df[cols].to_numpy(dtype=float))


def run(matches: pd.DataFrame, out_dir=config.OUTPUT_DIR, verbose=True,
        train_last=config.TRAIN_LAST_SEASON, valid_last=config.VALID_LAST_SEASON) -> dict:
    say = print if verbose else (lambda *a, **k: None)
    out_dir.mkdir(parents=True, exist_ok=True)

    say("1/6 Building pre-match features (Elo + recent form)...")
    df = build_features(matches)
    train, valid, test = chronological_split(df, train_last, valid_last)
    say(f"    train {len(train):,} | validation {len(valid):,} | test {len(test):,} matches")
    y_tr, y_va, y_te = (outcome_index(d.FTResult) for d in (train, valid, test))

    say("2/6 Training models on TRAIN, comparing on VALIDATION...")
    candidates = [EloBaseline()] + candidate_outcome_models()
    valid_rows = []
    for m in candidates:
        m.fit(train)
        valid_rows.append({"model": m.name, **ev.outcome_metrics(m.predict_proba(valid), y_va)})
    valid_table = pd.DataFrame(valid_rows)
    best_ml = min(candidates[1:], key=lambda m: valid_table.set_index("model").log_loss[m.name])
    say(valid_table[["model", "log_loss", "brier", "accuracy"]].round(4).to_string(index=False))
    say(f"    -> best scikit-learn model: {best_ml.name}")

    # Validation predictions from models trained on TRAIN only: used to choose the
    # betting threshold, so the threshold never sees the test seasons.
    valid_probs_ml = best_ml.predict_proba(valid)

    say("3/6 Refitting on TRAIN+VALIDATION, predicting TEST once...")
    trval = pd.concat([train, valid])
    elo_model = EloBaseline().fit(trval)
    ml_model = [m for m in candidate_outcome_models() if m.name == best_ml.name][0].fit(trval)
    goals_model = GoalsModel().fit(trval)
    p_elo, p_ml = elo_model.predict_proba(test), ml_model.predict_proba(test)
    goals = goals_model.predict(test)

    say("4/6 Comparing with bookmaker probabilities (margin removed)...")
    has_odds = test[BET365].notna().all(axis=1).to_numpy()
    t_odds = test[has_odds]
    yo = y_te[has_odds]
    p_mkt = market_probs(t_odds)
    p_mkt_pow = market_probs(t_odds, method="power")
    test_rows = []
    for name, p in [("Elo baseline", p_elo), (ml_model.name, p_ml), ("Poisson goals model (H/D/A)",
                    np.c_[goals["p_home_poisson"], goals["p_draw_poisson"], goals["p_away_poisson"]])]:
        test_rows.append({"model": name, "subset": "all test matches", **ev.outcome_metrics(p, y_te)})
        test_rows.append({"model": name, "subset": "matches with odds", **ev.outcome_metrics(p[has_odds], yo)})
    test_rows.append({"model": "Bookmaker (Bet365, proportional)", "subset": "matches with odds",
                      **ev.outcome_metrics(p_mkt, yo)})
    test_rows.append({"model": "Bookmaker (Bet365, power method)", "subset": "matches with odds",
                      **ev.outcome_metrics(p_mkt_pow, yo)})
    base = np.bincount(outcome_index(trval.FTResult), minlength=3) / len(trval)
    test_rows.append({"model": "Naive (historical H/D/A rates)", "subset": "all test matches",
                      **ev.outcome_metrics(np.tile(base, (len(test), 1)), y_te)})
    test_table = pd.DataFrame(test_rows)
    say(test_table[test_table.subset == "matches with odds"][["model", "log_loss", "brier", "accuracy",
                                                              "calibration_error"]].round(4).to_string(index=False))

    # Goals
    over = (test.FTHome + test.FTAway > 2).to_numpy().astype(int)
    has_ou = test[["Over25", "Under25"]].notna().all(axis=1).to_numpy()
    ou_mkt = remove_margin_proportional(test.loc[has_ou, ["Over25", "Under25"]].to_numpy(float))[:, 0]
    mean_goals_h, mean_goals_a = trval.FTHome.mean(), trval.FTAway.mean()
    goals_metrics = {
        "mae_home_goals_model": float(np.mean(np.abs(goals["exp_home_goals"] - test.FTHome))),
        "mae_away_goals_model": float(np.mean(np.abs(goals["exp_away_goals"] - test.FTAway))),
        "mae_home_goals_naive": float(np.mean(np.abs(mean_goals_h - test.FTHome))),
        "mae_away_goals_naive": float(np.mean(np.abs(mean_goals_a - test.FTAway))),
        "over25_brier_model": ev.binary_brier(goals["p_over25"][has_ou], over[has_ou]),
        "over25_brier_bookmaker": ev.binary_brier(ou_mkt, over[has_ou]),
        "over25_logloss_model": ev.binary_log_loss(goals["p_over25"][has_ou], over[has_ou]),
        "over25_logloss_bookmaker": ev.binary_log_loss(ou_mkt, over[has_ou]),
        "n_matches_with_ou_odds": int(has_ou.sum()),
    }

    say("5/6 Hypothetical flat-stake backtest (threshold chosen on VALIDATION)...")
    v_has = valid[BET365].notna().all(axis=1).to_numpy()
    threshold, valid_bt = bt.choose_threshold(valid_probs_ml[v_has], valid[v_has][BET365].to_numpy(float), y_va[v_has])
    t_bet365 = t_odds[BET365].to_numpy(float)
    rows = [bt.summarise(pd.DataFrame(columns=["profit", "won", "odds", "cumulative_profit"]), "No bet")]
    chosen_bets = pd.DataFrame()
    if threshold is not None:
        chosen_bets = bt.run_backtest(p_ml[has_odds], t_bet365, yo, threshold)
        rows.append(bt.summarise(chosen_bets, f"Chosen on validation: EV >= {threshold:.0%} (Bet365)"))
    # For transparency only (NOT used to choose anything): every threshold on test.
    for t in config.EDGE_THRESHOLDS:
        rows.append(bt.summarise(bt.run_backtest(p_ml[has_odds], t_bet365, yo, t),
                                 f"[info] EV >= {t:.0%} (Bet365)"))
    t_has_max = t_odds[MAXODDS].notna().all(axis=1).to_numpy()
    if t_has_max.any():
        t0 = threshold if threshold is not None else 0.05
        rows.append(bt.summarise(bt.run_backtest(p_ml[has_odds][t_has_max], t_odds[t_has_max][MAXODDS].to_numpy(float),
                                                 yo[t_has_max], t0),
                                 f"[optimistic] EV >= {t0:.0%} at BEST market price"))
    backtest_table = pd.DataFrame(rows)
    say(backtest_table[["strategy", "bets", "roi", "roi_ci_low", "roi_ci_high", "max_drawdown"]]
        .round(3).to_string(index=False))

    say("6/6 Saving outputs...")
    preds = test[["Division", "Season", "MatchDate", "HomeTeam", "AwayTeam", "FTHome", "FTAway", "FTResult",
                  *BET365]].copy()
    preds[["elo_pH", "elo_pD", "elo_pA"]] = p_elo
    preds[["ml_pH", "ml_pD", "ml_pA"]] = p_ml
    preds[["mkt_pH", "mkt_pD", "mkt_pA"]] = np.nan
    preds.loc[has_odds, ["mkt_pH", "mkt_pD", "mkt_pA"]] = p_mkt
    preds["bookmaker_overround"] = overround(test[BET365].to_numpy(float))
    preds["exp_home_goals"], preds["exp_away_goals"] = goals["exp_home_goals"], goals["exp_away_goals"]
    preds["p_over25"] = goals["p_over25"]
    preds.to_csv(out_dir / "test_predictions.csv", index=False)

    calib = pd.concat([ev.calibration_table(p_elo, y_te).assign(model="Elo baseline"),
                       ev.calibration_table(p_ml, y_te).assign(model=ml_model.name),
                       ev.calibration_table(p_mkt, yo).assign(model="Bookmaker (Bet365)")])
    calib.to_csv(out_dir / "calibration.csv", index=False)
    valid_table.to_csv(out_dir / "validation_metrics.csv", index=False)
    test_table.to_csv(out_dir / "test_metrics.csv", index=False)
    valid_bt.to_csv(out_dir / "validation_backtest.csv", index=False)
    backtest_table.to_csv(out_dir / "test_backtest.csv", index=False)
    if not chosen_bets.empty:
        tb = t_odds.iloc[chosen_bets.row.values]
        chosen_bets = chosen_bets.assign(MatchDate=tb.MatchDate.values, HomeTeam=tb.HomeTeam.values,
                                         AwayTeam=tb.AwayTeam.values, FTResult=tb.FTResult.values)
    chosen_bets.to_csv(out_dir / "test_bets.csv", index=False)

    summary = {
        "divisions": sorted(matches.Division.unique().tolist()),
        "train_seasons": [int(train.Season.min()), int(train.Season.max())],
        "valid_seasons": [int(valid.Season.min()), int(valid.Season.max())],
        "test_seasons": [int(test.Season.min()), int(test.Season.max())],
        "n_train": len(train), "n_valid": len(valid), "n_test": len(test),
        "n_test_with_odds": int(has_odds.sum()),
        "best_ml_model": ml_model.name,
        "chosen_threshold": threshold,
        "recommendation": ("NO BET - no threshold was profitable with enough bets on validation"
                           if threshold is None else f"Research only: EV >= {threshold:.0%}"),
        "mean_bookmaker_overround": float(np.nanmean(preds.bookmaker_overround)),
        "goals": goals_metrics,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    say(f"Done. Results in {out_dir}. Start the dashboard with:  streamlit run dashboard.py")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--divisions", nargs="+", default=config.DIVISIONS,
                        help="league codes, e.g. E0 E1 (default: %(default)s)")
    args = parser.parse_args()
    run(data.load(divisions=args.divisions))


if __name__ == "__main__":
    main()
