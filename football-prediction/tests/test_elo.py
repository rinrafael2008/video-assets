from footy.elo import Elo, expected_home_score


def test_equal_teams_without_home_advantage_is_fifty_fifty():
    assert expected_home_score(1500, 1500, home_advantage=0) == 0.5


def test_home_advantage_helps_home_team():
    assert expected_home_score(1500, 1500, home_advantage=60) > 0.5


def test_update_conserves_points_and_rewards_winner():
    elo = Elo(k=20, home_advantage=0)
    elo.update("A", "B", 2, 0)
    assert elo.ratings["A"] > 1500 > elo.ratings["B"]
    assert abs(elo.ratings["A"] + elo.ratings["B"] - 3000) < 1e-9


def test_draw_between_equal_teams_changes_nothing():
    elo = Elo(k=20, home_advantage=0)
    elo.update("A", "B", 1, 1)
    assert elo.ratings == {"A": 1500, "B": 1500}


def test_new_season_pulls_towards_mean():
    elo = Elo(season_regression=0.5)
    elo.ratings = {"A": 1600.0, "B": 1400.0}
    elo.new_season()
    assert elo.ratings == {"A": 1550.0, "B": 1450.0}


def test_neutral_venue_removes_home_advantage():
    elo = Elo(k=20, home_advantage=100)
    elo.update("A", "B", 1, 1, neutral=True)       # equal teams, neutral, draw -> no change
    assert elo.ratings == {"A": 1500, "B": 1500}
    elo.update("A", "B", 1, 1)                      # at home a draw is a disappointment
    assert elo.ratings["A"] < 1500


def test_bigger_k_moves_ratings_more():
    small, big = Elo(home_advantage=0), Elo(home_advantage=0)
    small.update("A", "B", 1, 0, k=10)
    big.update("A", "B", 1, 0, k=60)
    assert big.ratings["A"] - 1500 == 6 * (small.ratings["A"] - 1500)
