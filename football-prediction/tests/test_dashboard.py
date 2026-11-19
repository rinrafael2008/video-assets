"""Smoke test: the dashboard script runs without errors on pipeline output."""
import os
from pathlib import Path

from streamlit.testing.v1 import AppTest

from footy.pipeline import run

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard.py"


def test_dashboard_renders(tmp_path, monkeypatch, matches):
    run(matches, out_dir=tmp_path, verbose=False, train_last=2004, valid_last=2006)
    import footy.config
    monkeypatch.setattr(footy.config, "OUTPUT_DIR", tmp_path)
    at = AppTest.from_file(str(DASHBOARD), default_timeout=60).run()
    assert not at.exception, at.exception
    assert not at.error, [e.value for e in at.error]   # e.g. "No results yet"
    assert len(at.tabs) == 5
    assert any("never places real bets" in w.value for w in at.warning)
