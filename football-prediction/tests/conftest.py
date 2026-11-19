"""Shared test helpers. Tests use small SYNTHETIC data, so they run in seconds
and don't need the real dataset to be downloaded."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def make_matches(n_seasons=8, n_teams=10, seed=0, start_year=2001):
    """Fake league: each team has a hidden strength; goals are Poisson; odds have a 6% margin."""
    rng = np.random.default_rng(seed)
    teams = [f"Team{i}" for i in range(n_teams)]
    strength = dict(zip(teams, rng.normal(0, 0.4, n_teams)))
    rows = []
    for s in range(n_seasons):
        day = pd.Timestamp(f"{start_year + s}-08-01")
        for h in teams:
            for a in teams:
                if h == a:
                    continue
                lam_h = np.exp(0.3 + strength[h] - strength[a])
                lam_a = np.exp(0.05 + strength[a] - strength[h])
                hg, ag = rng.poisson(lam_h), rng.poisson(lam_a)
                fair = np.array([0.45, 0.27, 0.28]) + 0.15 * np.tanh(strength[h] - strength[a]) * np.array([1, 0, -1])
                odds = 1 / (fair * 1.06)
                rows.append({"Division": "E0", "MatchDate": day, "MatchTime": "15:00:00",
                             "HomeTeam": h, "AwayTeam": a, "FTHome": hg, "FTAway": ag,
                             "FTResult": "H" if hg > ag else ("D" if hg == ag else "A"),
                             "OddHome": odds[0], "OddDraw": odds[1], "OddAway": odds[2],
                             "MaxHome": odds[0] * 1.03, "MaxDraw": odds[1] * 1.03, "MaxAway": odds[2] * 1.03,
                             "Over25": 1.9, "Under25": 1.9})
                day += pd.Timedelta(days=2)
    from footy.data import clean
    return clean(pd.DataFrame(rows).assign(MatchDate=lambda d: d.MatchDate.dt.strftime("%Y-%m-%d")), ["E0"])


@pytest.fixture
def matches():
    return make_matches()
