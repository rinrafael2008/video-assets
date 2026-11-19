"""Smoke test: the dashboard runs without errors for club results, national-team
results (no odds), the league comparison and upcoming predictions."""
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from footy import international as intl
from footy.pipeline import run
from tests.test_international import make_intl

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard.py"


def test_dashboard_renders_every_results_folder(tmp_path, monkeypatch, matches):
    run(matches, out_dir=tmp_path, verbose=False, train_last=2004, valid_last=2006)
    run(matches, out_dir=tmp_path / "leagues" / "Fakeland", verbose=False, train_last=2004, valid_last=2006)
    pd.DataFrame({"league": ["Fakeland"], "model_minus_bookmaker": [0.01]}).to_csv(
        tmp_path / "leagues" / "league_comparison.csv", index=False)
    intl.run(make_intl(), out_dir=tmp_path / "international", verbose=False, train_start="2006-01-01",
             train_end="2010-12-31", valid_end="2013-12-31")
    import footy.config
    monkeypatch.setattr(footy.config, "OUTPUT_DIR", tmp_path)

    at = AppTest.from_file(str(DASHBOARD), default_timeout=60).run()
    options = at.sidebar.selectbox[0].options
    assert len(options) == 3
    for option in options:
        at.sidebar.selectbox[0].select(option).run()
        assert not at.exception, (option, at.exception)
        assert not at.error, [e.value for e in at.error]
        assert len(at.tabs) == 7
    assert any("never places real bets" in w.value for w in at.warning)
