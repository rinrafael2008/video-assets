import numpy as np
import pandas as pd

from footy import international as intl


def make_intl(n_years=12, seed=0):
    rng = np.random.default_rng(seed)
    teams = [f"Nation{i}" for i in range(12)]
    strength = dict(zip(teams, rng.normal(0, 0.5, len(teams))))
    rows, day = [], pd.Timestamp("2005-01-01")
    for _ in range(n_years * 60):
        h, a = rng.choice(teams, 2, replace=False)
        neutral = rng.random() < 0.3
        lam_h = np.exp(0.1 + (0 if neutral else 0.25) + strength[h] - strength[a])
        lam_a = np.exp(0.1 + strength[a] - strength[h])
        rows.append({"date": day.strftime("%Y-%m-%d"), "home_team": h, "away_team": a,
                     "home_score": rng.poisson(lam_h), "away_score": rng.poisson(lam_a),
                     "tournament": rng.choice(["Friendly", "FIFA World Cup qualification", "FIFA World Cup"]),
                     "city": "x", "country": "x", "neutral": "TRUE" if neutral else "FALSE"})
        day += pd.Timedelta(days=6)
    return intl.clean(pd.DataFrame(rows))


def test_importance_and_goal_multiplier():
    assert intl.importance_k("FIFA World Cup") > intl.importance_k("UEFA Euro qualification") > \
        intl.importance_k("Friendly")
    assert intl.goal_difference_multiplier(1, 0) == 1 and intl.goal_difference_multiplier(3, 1) == 1.5
    assert intl.goal_difference_multiplier(5, 0) == 2.0


def test_intl_features_have_no_leakage():
    m = make_intl()
    i = len(m) // 2
    a = intl.build_features(m)
    t = m.copy()
    t.loc[i, ["FTHome", "FTAway"]] = [7, 0]
    b = intl.build_features(t)
    pd.testing.assert_frame_equal(a.loc[:i, intl.INTL_FEATURES], b.loc[:i, intl.INTL_FEATURES])


def test_neutral_matches_get_no_home_edge():
    f = intl.build_features(make_intl())
    neutral = f[f.neutral == 1]
    assert np.allclose(neutral.elo_diff, neutral.elo_home - neutral.elo_away)


def test_intl_pipeline_runs(tmp_path):
    s = intl.run(make_intl(), out_dir=tmp_path, verbose=False, train_start="2006-01-01",
                 train_end="2010-12-31", valid_end="2013-12-31")
    assert s["n_test"] > 0 and s["n_test_with_odds"] == 0
    t = pd.read_csv(tmp_path / "test_metrics.csv")
    model = t[(t.model == s["best_ml_model"]) & (t.subset == "all test matches")].log_loss.iloc[0]
    naive = t[(t.model.str.startswith("Naive")) & (t.subset == "all test matches")].log_loss.iloc[0]
    assert model < naive                     # learns something real from the fake strengths
    assert not (tmp_path / "test_backtest.csv").exists()
