"""Step 6: a HYPOTHETICAL flat-stake value-betting simulation. No real bets, ever.

"Value" means: our probability x the bookmaker's odds > 1, i.e. we think the
price is too generous. Expected value per 1 unit staked:

    EV = p_model * odds - 1

Rule: for each match, look at the outcome with the highest EV. If EV is at least
`threshold`, pretend to stake 1 unit on it; otherwise skip the match (no bet).

"No bet" is a full strategy option too: if nothing looks reliably profitable on
the validation seasons, the honest recommendation is to not bet at all.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from footy import config
from footy.models import OUTCOMES


def select_bets(probs, odds, threshold, min_odds=config.MIN_ODDS, max_odds=config.MAX_ODDS):
    """Return (bet_mask, chosen_outcome_index, ev_of_choice) for every match."""
    probs = np.asarray(probs, dtype=float)
    odds = np.asarray(odds, dtype=float)
    ev = probs * odds - 1
    ev = np.where((odds >= min_odds) & (odds <= max_odds), ev, -np.inf)  # also drops NaN odds
    choice = np.argmax(ev, axis=1)
    best_ev = ev[np.arange(len(ev)), choice]
    return best_ev >= threshold, choice, best_ev


def run_backtest(probs, odds, y_idx, threshold, stake=config.STAKE) -> pd.DataFrame:
    """One row per (hypothetical) bet, in date order, with running profit."""
    bet, choice, best_ev = select_bets(probs, odds, threshold)
    idx = np.flatnonzero(bet)
    odds = np.asarray(odds, dtype=float)
    won = choice[idx] == np.asarray(y_idx)[idx]
    price = odds[idx, choice[idx]]
    profit = np.where(won, stake * (price - 1), -stake)
    return pd.DataFrame({"row": idx, "pick": [OUTCOMES[c] for c in choice[idx]],
                         "odds": price, "expected_value": best_ev[idx], "won": won,
                         "profit": profit, "cumulative_profit": np.cumsum(profit)})


def max_drawdown(cumulative_profit) -> float:
    """Largest fall from a previous peak (starting bankroll counts as a peak of 0)."""
    c = np.concatenate([[0.0], np.asarray(cumulative_profit, dtype=float)])
    return float(np.max(np.maximum.accumulate(c) - c))


def bootstrap_roi(profits, stake=config.STAKE, n=config.BOOTSTRAP_SAMPLES, seed=config.RANDOM_SEED):
    """Resample the bets with replacement many times to see how much ROI could
    vary just by luck. Returns (low 2.5%, high 97.5%, share of resamples with ROI > 0)."""
    profits = np.asarray(profits, dtype=float)
    if len(profits) == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    samples = rng.choice(profits, size=(n, len(profits)), replace=True).mean(axis=1) / stake
    return float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5)), float((samples > 0).mean())


def summarise(bets: pd.DataFrame, label: str, stake=config.STAKE) -> dict:
    n = len(bets)
    if n == 0:
        return {"strategy": label, "bets": 0, "staked": 0.0, "profit": 0.0, "roi": 0.0,
                "hit_rate": float("nan"), "avg_odds": float("nan"), "max_drawdown": 0.0,
                "roi_ci_low": 0.0, "roi_ci_high": 0.0, "p_roi_positive": float("nan")}
    lo, hi, p_pos = bootstrap_roi(bets.profit.values, stake)
    return {"strategy": label, "bets": n, "staked": n * stake,
            "profit": float(bets.profit.sum()), "roi": float(bets.profit.sum() / (n * stake)),
            "hit_rate": float(bets.won.mean()), "avg_odds": float(bets.odds.mean()),
            "max_drawdown": max_drawdown(bets.cumulative_profit.values),
            "roi_ci_low": lo, "roi_ci_high": hi, "p_roi_positive": p_pos}


def choose_threshold(valid_probs, valid_odds, valid_y, thresholds=config.EDGE_THRESHOLDS,
                     min_bets=config.MIN_BETS_FOR_STRATEGY):
    """Pick the threshold using VALIDATION data only. Returns (threshold or None, table).
    None means the no-bet option won: nothing was both profitable and well-sampled."""
    rows = [summarise(run_backtest(valid_probs, valid_odds, valid_y, t), f"EV >= {t:.0%}") | {"threshold": t}
            for t in thresholds]
    table = pd.DataFrame(rows)
    ok = table[(table.bets >= min_bets) & (table.roi > 0)]
    if ok.empty:
        return None, table
    return float(ok.sort_values("roi", ascending=False).threshold.iloc[0]), table
