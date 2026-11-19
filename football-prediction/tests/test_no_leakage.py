"""The most important tests: features must not depend on the match's own result
or on anything that happened later."""
import numpy as np
import pandas as pd

from footy.features import FEATURE_COLUMNS, SHOT_COLUMNS, build_features
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
    forbidden = {"FTHome", "FTAway", "FTResult", "HTHome", "HomeShots", "HomeTarget", "HomeElo", "Form5Home",
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


def test_future_fixtures_get_features_but_change_nothing(matches):
    with_fixture = pd.concat([matches, matches.tail(1).assign(FTHome=np.nan, FTAway=np.nan, FTResult=None)],
                             ignore_index=True)
    a = build_features(matches)
    b = build_features(with_fixture)
    pd.testing.assert_frame_equal(a[FEATURE_COLUMNS], b.iloc[:-1][FEATURE_COLUMNS])
    assert b.iloc[-1][FEATURE_COLUMNS].notna().all()      # last season has shot data


def test_a_matchs_own_shots_never_reach_its_features(matches):
    i = len(matches) - 50
    a = build_features(matches)
    t = matches.copy()
    t.loc[i, ["HomeShots", "HomeTarget"]] = [60, 40]          # absurd numbers for match i only
    b = build_features(t)
    pd.testing.assert_frame_equal(a.loc[:i, SHOT_COLUMNS], b.loc[:i, SHOT_COLUMNS])
    home = matches.loc[i, "HomeTeam"]
    later = b.index[(b.index > i) & ((b.HomeTeam == home) | (b.AwayTeam == home))][0]
    assert not a.loc[later, SHOT_COLUMNS].equals(b.loc[later, SHOT_COLUMNS])   # ...but later matches see them


def test_shot_features_missing_where_no_shot_data(matches):
    f = build_features(matches)
    assert f.loc[f.Season <= 2003, SHOT_COLUMNS].isna().all().all()
    assert f.loc[f.Season >= 2005, SHOT_COLUMNS].notna().all().all()
