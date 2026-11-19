import numpy as np
import pandas as pd

from footy import backtest as bt


def test_max_drawdown():
    assert bt.max_drawdown([1, 3, 2, -1, 4]) == 4      # peak 3 -> trough -1
    assert bt.max_drawdown([-1, -2]) == 2              # starting bankroll is a peak
    assert bt.max_drawdown([1, 2, 3]) == 0


def test_flat_stake_profit_and_value_rule():
    probs = np.array([[0.6, 0.2, 0.2],    # EV home = 0.6*2.0-1 = +0.20 -> bet, wins
                      [0.3, 0.3, 0.4],    # EV best = 0.4*2.0-1 = -0.20 -> no bet
                      [0.5, 0.25, 0.25]]) # EV home = +0.25 -> bet, loses
    odds = np.array([[2.0, 3.0, 4.0], [3.0, 3.0, 2.0], [2.5, 3.0, 3.0]])
    y = np.array([0, 2, 1])
    bets = bt.run_backtest(probs, odds, y, threshold=0.05)
    assert list(bets.row) == [0, 2]
    assert list(bets.profit) == [1.0, -1.0]
    s = bt.summarise(bets, "x")
    assert s["bets"] == 2 and s["roi"] == 0 and s["max_drawdown"] == 1


def test_missing_odds_are_never_bet():
    bets = bt.run_backtest(np.array([[0.9, 0.05, 0.05]]), np.array([[np.nan, 3, 3]]), np.array([0]), 0.0)
    assert bets.empty


def test_no_bet_chosen_when_model_has_no_edge():
    rng = np.random.default_rng(1)
    n = 3000
    true_p = rng.dirichlet([4, 3, 3], size=n)
    y = np.array([rng.choice(3, p=p) for p in true_p])
    odds = 1 / (true_p * 1.06)                      # bookmaker knows the truth and takes a margin
    noisy = true_p * rng.uniform(0.9, 1.1, size=true_p.shape)
    noisy /= noisy.sum(axis=1, keepdims=True)       # our model = truth + noise -> no real edge
    threshold, table = bt.choose_threshold(noisy, odds, y)
    assert threshold is None
    assert len(table) == 6


def test_summary_of_no_bets_is_zero():
    s = bt.summarise(pd.DataFrame(columns=["profit", "won", "odds", "cumulative_profit"]), "No bet")
    assert s["bets"] == 0 and s["roi"] == 0 and s["max_drawdown"] == 0


def test_bootstrap_interval_contains_mean():
    profits = np.r_[np.full(60, -1.0), np.full(40, 1.2)]
    lo, hi, _ = bt.bootstrap_roi(profits)
    assert lo < profits.mean() < hi
