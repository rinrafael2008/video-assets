"""Run the full pipeline for every main league, plus one model pooled over all of them.

    python -m footy.study

Each league gets its own folder in outputs/leagues/<Country>/ (the dashboard can open
any of them), and outputs/leagues/league_comparison.csv puts them side by side.
Every league uses the same rules: same seasons for train/validation/test, betting
threshold chosen on validation only, and "No bet" whenever nothing qualifies.
"""
from __future__ import annotations

import argparse

import pandas as pd

from footy import config, data
from footy.pipeline import run

LEAGUES_DIR = config.OUTPUT_DIR / "leagues"


def comparison_row(name: str, out_dir) -> dict:
    s = pd.read_json(out_dir / "summary.json", typ="series")
    t = pd.read_csv(out_dir / "test_metrics.csv")
    t = t[t.subset == "matches with odds"].set_index("model")
    b = pd.read_csv(out_dir / "test_backtest.csv").set_index("strategy")
    ml = s["best_ml_model"]
    info5 = b.loc["[info] EV >= 5% (Bet365)"] if "[info] EV >= 5% (Bet365)" in b.index else None
    return {
        "league": name,
        "test_matches_with_odds": int(s["n_test_with_odds"]),
        "logloss_elo": t.loc["Elo baseline", "log_loss"],
        "logloss_model": t.loc[ml, "log_loss"],
        "logloss_bookmaker": t.loc["Bookmaker (Bet365, proportional)", "log_loss"],
        "model_minus_bookmaker": t.loc[ml, "log_loss"] - t.loc["Bookmaker (Bet365, proportional)", "log_loss"],
        "bookmaker_margin": s["mean_bookmaker_overround"] - 1,
        "strategy_chosen_on_validation": "NO BET" if pd.isna(s["chosen_threshold"]) or s["chosen_threshold"] is None
        else f"EV >= {s['chosen_threshold']:.0%}",
        "info_roi_ev5": None if info5 is None else info5["roi"],
        "info_roi_ev5_ci": None if info5 is None else f"{info5['roi_ci_low']:.1%} to {info5['roi_ci_high']:.1%}",
        "info_bets_ev5": None if info5 is None else int(info5["bets"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--leagues", nargs="+", default=list(config.LEAGUE_GROUPS),
                        help="countries from config.LEAGUE_GROUPS (default: all)")
    parser.add_argument("--no-pooled", action="store_true", help="skip the all-leagues pooled model")
    args = parser.parse_args()

    raw = data.load_raw()
    rows = []
    groups = {c: config.LEAGUE_GROUPS[c] for c in args.leagues}
    if not args.no_pooled and len(groups) > 1:
        groups["All main leagues (pooled)"] = sorted({d for c in groups.values() for d in c})
    for country, divisions in groups.items():
        print(f"\n===== {country}: {', '.join(divisions)} =====")
        out = LEAGUES_DIR / country
        run(data.clean(raw, divisions), out_dir=out, verbose=False)
        rows.append(comparison_row(country, out))
        r = rows[-1]
        print(f"model log loss {r['logloss_model']:.4f} | bookmaker {r['logloss_bookmaker']:.4f} | "
              f"strategy: {r['strategy_chosen_on_validation']}")
    table = pd.DataFrame(rows)
    table.to_csv(LEAGUES_DIR / "league_comparison.csv", index=False)
    print("\n" + table[["league", "test_matches_with_odds", "logloss_model", "logloss_bookmaker",
                        "strategy_chosen_on_validation", "info_roi_ev5"]].round(4).to_string(index=False))
    print(f"\nSaved {LEAGUES_DIR / 'league_comparison.csv'}")


if __name__ == "__main__":
    main()
