"""Turning bookmaker odds into probabilities.

Decimal odds of 2.50 mean: stake 1, get 2.50 back if you win. The "implied
probability" is 1 / 2.50 = 0.40. But for a 1X2 market the three implied
probabilities add up to MORE than 1 (e.g. 1.05). That extra 5% is the
bookmaker's margin ("overround"). To compare fairly with our model we remove it.
"""
from __future__ import annotations

import numpy as np


def implied_probabilities(odds) -> np.ndarray:
    return 1.0 / np.asarray(odds, dtype=float)


def overround(odds) -> np.ndarray:
    return implied_probabilities(odds).sum(axis=-1)


def remove_margin_proportional(odds) -> np.ndarray:
    """Simplest method: scale the implied probabilities so they sum to 1."""
    p = implied_probabilities(odds)
    return p / p.sum(axis=-1, keepdims=True)


def remove_margin_power(odds, iterations: int = 60) -> np.ndarray:
    """'Power' method: find k so that sum(p_i ** k) == 1.

    Bookmakers tend to put relatively more margin on long shots (the
    favourite-longshot bias); the power method shrinks long shots more than
    favourites, which usually matches reality slightly better.
    """
    p = np.atleast_2d(implied_probabilities(odds))
    out = np.full_like(p, np.nan)
    for i, row in enumerate(p):
        if np.isnan(row).any():
            continue
        lo, hi = 0.1, 10.0   # k < 1 if odds sum below 1 (rare)
        for _ in range(iterations):          # bisection: sum(row**k) decreases as k grows
            k = (lo + hi) / 2
            if (row ** k).sum() > 1:
                lo = k
            else:
                hi = k
        q = row ** ((lo + hi) / 2)
        out[i] = q / q.sum()
    return out.reshape(np.shape(implied_probabilities(odds)))
