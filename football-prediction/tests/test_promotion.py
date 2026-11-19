"""Promoted/relegated teams: detected from the division change at the start of a season,
rating shifted once, and flagged for that whole season."""
import pandas as pd

from footy.elo import Elo
from footy.features import build_features


def season_rows(season, division, pairs, start_day):
    return [{"Division": division, "MatchDate": pd.Timestamp(f"{season}-08-01") + pd.Timedelta(days=start_day + i),
             "Season": season, "HomeTeam": h, "AwayTeam": a, "FTHome": 1, "FTAway": 1, "FTResult": "D"}
            for i, (h, a) in enumerate(pairs)]


def two_seasons():
    rows = (season_rows(2020, "E1", [("Up", "B"), ("B", "Up")], 0) +            # Up plays in the Championship
            season_rows(2020, "E0", [("Down", "C"), ("C", "Down")], 0) +       # Down plays in the Premier League
            season_rows(2021, "E0", [("Up", "C"), ("C", "Up")], 0) +           # Up promoted
            season_rows(2021, "E1", [("Down", "B"), ("B", "Down")], 0))        # Down relegated
    return pd.DataFrame(rows).sort_values("MatchDate", kind="stable").reset_index(drop=True)


def test_change_division_shifts_rating():
    elo = Elo(promotion_shift=-100)
    elo.ratings = {"A": 1500.0, "B": 1500.0}
    elo.change_division("A", promoted=True)
    elo.change_division("B", promoted=False)
    assert elo.ratings == {"A": 1400.0, "B": 1600.0}


def test_promotion_flags_and_shift():
    m = two_seasons()
    f = build_features(m, Elo(promotion_shift=-100, season_regression=0))
    up_2021 = f[(f.Season == 2021) & (f.HomeTeam == "Up")].iloc[0]
    assert up_2021.home_promoted == 1 and up_2021.home_relegated == 0
    up_away = f[(f.Season == 2021) & (f.AwayTeam == "Up")].iloc[0]         # flag lasts the whole season
    assert up_away.away_promoted == 1
    down = f[(f.Season == 2021) & (f.HomeTeam == "Down")].iloc[0]
    assert down.home_relegated == 1 and down.home_promoted == 0
    assert f[f.Season == 2020][["home_promoted", "away_promoted"]].sum().sum() == 0
    # all draws between equal teams -> only the division change moved the ratings
    assert abs(up_2021.elo_home - 1400) < 1 and abs(down.elo_home - 1600) < 1


def test_no_shift_when_setting_is_zero():
    f = build_features(two_seasons(), Elo(promotion_shift=0, season_regression=0))
    assert abs(f[(f.Season == 2021) & (f.HomeTeam == "Up")].iloc[0].elo_home - 1500) < 1


def test_table_context():
    from footy.features import table_context
    # 6-team league: 10 games each. Leader 25 pts, team "Mid" 15, bottom 3 have 5, 4, 3.
    table = {"Top": [25, 9, 15], "Second": [20, 9, 8], "Mid": [15, 9, 0],
             "Low1": [5, 9, -5], "Low2": [4, 9, -8], "Low3": [3, 9, -10]}
    c = table_context(table, "Mid", n_teams=6)
    assert c["table_pos"] == 2 / 5
    assert c["title_gap"] == (25 - 15) / (3 * 1 + 1)       # 10 points behind with 3 points left: impossible
    assert c["drop_margin"] == (15 - 5) / 4                 # 10 points above the drop line
    assert c["nothing_to_play"] == 1.0
    top = table_context(table, "Top", n_teams=6)
    assert top["title_gap"] == 0 and top["nothing_to_play"] == 0.0
    early = table_context({}, "New", n_teams=20)
    assert early["progress"] == 0 and early["nothing_to_play"] == 0.0
