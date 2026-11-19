"""The most important tests: features must not depend on the match's own result
or on anything that happened later."""
import numpy as np
import pandas as pd

from footy.features import FEATURE_COLUMNS, build_features
from footy.split import chronological_split


def test_changing_a_result_does_not_change_its_own_or_earlier_features(matches):
    i = len(matches) // 2
    original = build_features(matches)
    tampered = matches.copy()
    tampered.loc[i, ["FTHome", "FTAway"]] = [9, 0]   # rewrite match i's result
    changed = build_features(tampered)
    pd.testing.assert_frame_equal(original.loc[:i, FEATURE_COLUMNS], changed.loc[:i, FEATURE_COLUMNS])
    # ...but later matches of those teams SHOULD now see different form/Elo
    assert not original.loc[i + 1:, FEATURE_COLUMNS].equals(changed.loc[i + 1:, FEATURE_COLUMNS])


def test_deleting_the_future_does_not_change_the_past(matches):
    cut = len(matches) // 3
    full = build_features(matches)
    past_only = build_features(matches.iloc[:cut].copy())
    pd.testing.assert_frame_equal(full.loc[:cut - 1, FEATURE_COLUMNS], past_only[FEATURE_COLUMNS])


def test_features_do_not_use_match_statistics():
    forbidden = {"FTHome", "FTAway", "FTResult", "HTHome", "HomeShots", "HomeElo", "Form5Home",
                 "OddHome", "MaxHome", "C_LTH"}
    assert forbidden.isdisjoint(FEATURE_COLUMNS)


def test_first_match_has_no_history(matches):
    first = build_features(matches).iloc[0]
    assert np.isnan(first.home_pts_avg) and first.home_games_played == 0


def test_split_is_chronological_and_disjoint(matches):
    df = build_features(matches)
    train, valid, test = chronological_split(df, train_last=2004, valid_last=2006, burn_in=1)
    assert train.MatchDate.max() < valid.MatchDate.min()
    assert valid.MatchDate.max() < test.MatchDate.min()
    assert set(train.index).isdisjoint(valid.index) and set(valid.index).isdisjoint(test.index)
    assert train.Season.min() == 2002            # burn-in season dropped
    assert len(train) + len(valid) + len(test) == (df.Season >= 2002).sum()
