"""Step 3: chronological train / validation / test split.

We never shuffle. The model learns from the past (train), we choose settings on
the "recent past" (validation), and we measure final performance ONCE on the
most recent seasons (test), which the model has never seen.
"""
from __future__ import annotations

import pandas as pd

from footy import config


def chronological_split(df: pd.DataFrame,
                        train_last=config.TRAIN_LAST_SEASON,
                        valid_last=config.VALID_LAST_SEASON,
                        burn_in=config.BURN_IN_SEASONS):
    first = df["Season"].min()
    train = df[(df.Season >= first + burn_in) & (df.Season <= train_last)]
    valid = df[(df.Season > train_last) & (df.Season <= valid_last)]
    test = df[df.Season > valid_last]
    assert train.MatchDate.max() < valid.MatchDate.min() <= valid.MatchDate.max() < test.MatchDate.min(), \
        "splits overlap in time"
    return train.copy(), valid.copy(), test.copy()
