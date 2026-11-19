"""End-to-end smoke test on synthetic data: everything runs and files appear."""
import json

import numpy as np
import pandas as pd

from footy.features import build_features
from footy.models import EloBaseline, GoalsModel, candidate_outcome_models
from footy.pipeline import run


def test_models_output_valid_probabilities(matches):
    df = build_features(matches)
    train, test = df[df.Season < 2006], df[df.Season >= 2006]
    for m in [EloBaseline()] + candidate_outcome_models():
        p = m.fit(train).predict_proba(test)
        assert p.shape == (len(test), 3)
        assert np.allclose(p.sum(axis=1), 1) and (p >= 0).all()
    g = GoalsModel().fit(train).predict(test)
    assert (g["exp_home_goals"] > 0).all()
    assert ((0 <= g["p_over25"]) & (g["p_over25"] <= 1)).all()
    hda = g["p_home_poisson"] + g["p_draw_poisson"] + g["p_away_poisson"]
    assert np.allclose(hda, 1, atol=1e-3)


def test_full_pipeline_runs(tmp_path, matches):
    summary = run(matches, out_dir=tmp_path, verbose=False, train_last=2004, valid_last=2006)
    for f in ["summary.json", "test_predictions.csv", "calibration.csv", "test_metrics.csv",
              "test_backtest.csv", "validation_backtest.csv"]:
        assert (tmp_path / f).exists(), f
    assert json.loads((tmp_path / "summary.json").read_text())["n_test"] == summary["n_test"] > 0
    bt = pd.read_csv(tmp_path / "test_backtest.csv")
    assert bt.strategy.iloc[0] == "No bet"
