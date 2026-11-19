"""Tune the Elo settings on the VALIDATION seasons (never the test seasons).

    python -m footy.tune_elo

For every combination of K, home advantage, summer pull-to-average and promotion shift it:
  1. computes Elo ratings for every main league (fast Elo-only mode),
  2. fits the Elo baseline (rating difference -> home/draw/away) on the TRAIN seasons,
  3. scores it by log loss on the VALIDATION seasons, over all leagues together.
The best combination is printed; copy it into footy/config.py (ELO_* settings).
One shared setting for all leagues keeps it simple and avoids fitting noise in small leagues.
"""
from __future__ import annotations

import itertools
from multiprocessing import Pool

import numpy as np
import pandas as pd

from footy import config, data, evaluate as ev
from footy.elo import Elo
from footy.features import build_features
from footy.models import EloBaseline, outcome_index
from footy.split import chronological_split

GRID = {   # a first, wider search found the best values at the low-K / high-home-advantage edge
    "k": [8, 10, 12, 15],
    "home_advantage": [70, 80, 95, 110],
    "season_regression": [0.0, 0.05, 0.1],
    "promotion_shift": [0, -25, -50, -75],
}
_LEAGUES: dict = {}


def _init(leagues):
    _LEAGUES.update(leagues)


def score(settings: dict, leagues: dict | None = None) -> dict:
    """Validation log loss (match-weighted over leagues) of the Elo baseline with these settings."""
    leagues = leagues or _LEAGUES
    total, n = 0.0, 0
    for matches in leagues.values():
        df = build_features(matches, Elo(**settings), only_elo=True)
        train, valid, _ = chronological_split(df)
        model = EloBaseline().fit(train)
        total += ev.log_loss(model.predict_proba(valid), outcome_index(valid.FTResult)) * len(valid)
        n += len(valid)
    return {**settings, "valid_log_loss": total / n, "valid_matches": n}


def main():
    raw = data.load_raw()
    leagues = {c: data.clean(raw, divs) for c, divs in config.LEAGUE_GROUPS.items()}
    combos = [dict(zip(GRID, v)) for v in itertools.product(*GRID.values())]
    current = {"k": config.ELO_K, "home_advantage": config.ELO_HOME_ADVANTAGE,
               "season_regression": config.ELO_SEASON_REGRESSION, "promotion_shift": config.ELO_PROMOTION_SHIFT}
    print(f"Trying {len(combos)} Elo settings on the validation seasons of {len(leagues)} leagues...")
    with Pool(initializer=_init, initargs=(leagues,)) as pool:
        results = pool.map(score, combos + [current])
    table = pd.DataFrame(results[:-1]).sort_values("valid_log_loss").reset_index(drop=True)
    table.to_csv(config.OUTPUT_DIR / "elo_tuning.csv", index=False)
    print(table.head(10).round(5).to_string(index=False))
    best = table.iloc[0]
    print(f"\nCurrent settings: validation log loss {results[-1]['valid_log_loss']:.5f}")
    print(f"Best settings:    validation log loss {best.valid_log_loss:.5f}  ->  in footy/config.py set\n"
          f"  ELO_K = {best.k:g}\n  ELO_HOME_ADVANTAGE = {best.home_advantage:g}\n"
          f"  ELO_SEASON_REGRESSION = {best.season_regression:g}\n  ELO_PROMOTION_SHIFT = {best.promotion_shift:g}")


if __name__ == "__main__":
    main()
