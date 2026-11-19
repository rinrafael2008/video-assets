import numpy as np
import pandas as pd
import pytest

from footy.upcoming import predict


def fixtures(rows):
    return pd.DataFrame(rows, columns=["Division", "MatchDate", "HomeTeam", "AwayTeam",
                                       "OddHome", "OddDraw", "OddAway", "Bookmaker", "FTHome", "FTAway"])


def test_predicts_upcoming_and_compares_with_entered_odds(matches):
    fx = fixtures([["E0", "2009-08-01", "Team1", "Team2", 2.1, 3.3, 3.6, "Stoiximan", None, None],
                   ["E0", "2009-08-01", "Team3", "Team4", None, None, None, "", None, None]])
    out, _ = predict(matches, fx)
    assert len(out) == 2
    assert np.allclose(out[["model_pH", "model_pD", "model_pA"]].sum(axis=1), 1)
    assert np.isclose(out.loc[0, ["book_pH", "book_pD", "book_pA"]].sum(), 1)
    assert out.loc[0, "bookmaker_margin"] == pytest.approx(1 / 2.1 + 1 / 3.3 + 1 / 3.6 - 1)
    assert out.loc[1, "research_note"] == "no odds entered"
    assert "not a bet signal" in " ".join(out.research_note) or "agrees" in out.loc[0, "research_note"]


def test_result_rows_update_ratings(matches):
    up = ["E0", "2009-08-10", "Team1", "Team2", 2.0, 3.3, 3.8, "", None, None]
    before, _ = predict(matches, fixtures([up]))
    results = [["E0", "2009-08-01", "Team1", "Team9", None, None, None, "", 6, 0],
               ["E0", "2009-08-03", "Team1", "Team8", None, None, None, "", 5, 0]]
    after, _ = predict(matches, fixtures(results + [up]))
    assert len(after) == 1                                   # result rows are not predicted
    assert after.model_pH.iloc[0] > before.model_pH.iloc[0]  # two big wins -> stronger Team1


def test_unknown_team_gets_suggestion_and_case_is_fixed(matches):
    with pytest.raises(ValueError, match="Did you mean: Team1"):
        predict(matches, fixtures([["E0", "2009-08-01", "Teem1", "Team2", 2, 3, 4, "", None, None]]))
    out, warnings = predict(matches, fixtures([["E0", "2009-08-01", "team1", "TEAM2", 2, 3, 4, "", None, None]]))
    assert out.HomeTeam.iloc[0] == "Team1" and out.AwayTeam.iloc[0] == "Team2"
    assert any("team1" in w for w in warnings)


def test_stale_data_warning(matches):
    _, warnings = predict(matches, fixtures([["E0", "2012-01-01", "Team1", "Team2", 2, 3, 4, "", None, None]]))
    assert any("days before your first upcoming match" in w for w in warnings)
